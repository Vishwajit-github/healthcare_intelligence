from contextlib import asynccontextmanager
from typing import Any, Dict, Optional
import uuid
import traceback
from pathlib import Path
import shutil

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from graph.builder import graph
from src.utils.logger import get_chat_history
import time

# =========================================================
# UPLOAD DIRECTORY
# =========================================================

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# =========================================================
# RESPONSE SCHEMA
# =========================================================

class HealthcareResponse(BaseModel):
    request_id: str
    run_id: str
    status: str
    final_response: str
    validator: Optional[Dict[str, Any]] = None
    task_outputs: Optional[Any] = None


# =========================================================
# APP LIFECYCLE
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("\n" + "=" * 70)
    print("Starting Healthcare Multi-Agent LangGraph API")
    print("=" * 70 + "\n")

    yield

    print("\n" + "=" * 70)
    print("Stopping Healthcare Multi-Agent LangGraph API")
    print("=" * 70 + "\n")


app = FastAPI(
    title="Healthcare Multi-Agent AI API",
    description="Production-grade healthcare orchestration system using LangGraph + LangChain",
    version="2.0.0",
    lifespan=lifespan,
)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Healthcare Multi-Agent AI</title>
  <style>
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f7fafc;
      color: #102033;
    }
    main {
      width: min(720px, calc(100vw - 32px));
      padding: 40px;
      border-radius: 20px;
      background: white;
      box-shadow: 0 20px 60px rgba(16, 32, 51, 0.12);
    }
    h1 {
      margin: 0 0 12px;
      font-size: 34px;
    }
    p {
      margin: 0 0 24px;
      color: #526173;
      line-height: 1.6;
    }
    a {
      display: inline-block;
      padding: 12px 18px;
      border-radius: 10px;
      background: #0f766e;
      color: white;
      font-weight: 700;
      text-decoration: none;
    }
    .secondary {
      margin-left: 10px;
      background: #e2e8f0;
      color: #102033;
    }
  </style>
</head>
<body>
  <main>
    <h1>Healthcare Multi-Agent AI</h1>
    <p>
      The API is running. Open the Streamlit UI to ask healthcare questions,
      upload medical files, and view specialist agent outputs.
    </p>
    <a href="http://localhost:8001" target="_blank" rel="noreferrer">Open Streamlit UI</a>
    <a class="secondary" href="/docs">API Docs</a>
  </main>
</body>
</html>
"""


@app.get("/health")
async def health():
    return {"status": "healthy"}


# =========================================================
# FILE TYPE DETECTION
# =========================================================

def get_file_type(file_path: str, mime_type: str = None):

    ext = Path(file_path).suffix.lower()

    if ext in [".png", ".jpg", ".jpeg", ".webp"]:
        return "image"

    if ext == ".pdf":
        return "pdf"

    if ext in [".doc", ".docx"]:
        return "doc"

    return "text"


# =========================================================
# GENERIC FILE UPLOAD + ANALYZE ENDPOINT
# =========================================================

@app.post("/run", response_model=HealthcareResponse)
async def analyze_healthcare_query(

    user_query: str = Form(...),
    run_id: Optional[str] = Form(None),

    file: UploadFile = File(None),

):

    request_id = str(uuid.uuid4())
    run_id = run_id or str(uuid.uuid4())

    try:

        # =====================================================
        # SAVE FILE (IMAGE / PDF / DOC / DOCX)
        # =====================================================

        file_path = None
        file_mime_type = None

        if file:

            file_path = UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            file_path = str(file_path)
            file_mime_type = file.content_type

            print("\n📁 FILE SAVED:", file_path)

        # =====================================================
        # CHAT HISTORY
        # =====================================================

        history = get_chat_history(run_id=run_id, limit=6)

        # =====================================================
        # USER MESSAGE
        # =====================================================

        user_content = user_query

        if file_path:
            user_content += f"""

Medical file uploaded.

File path: {file_path}
File type: {get_file_type(file_path, file_mime_type)}

Question: {user_query}
"""

        messages = history + [
            {
                "role": "user",
                "content": user_content,
            }
        ]

        # =====================================================
        # GRAPH STATE
        # =====================================================

        initial_state = {

            # SESSION
            "run_id": run_id,

            # INPUT
            "user_query": user_query,
            "messages": messages,

            # FILE INPUT (NEW UNIFIED FIELD)
            "uploaded_file_path": file_path,
            "uploaded_file_type": get_file_type(file_path, file_mime_type) if file_path else None,
            "uploaded_file_mime_type": file_mime_type,

            # AGENTS
            "supervisor_output": None,
            "validation_result": None,
            "validation_risk_level": None,
            "is_valid": False,
            "iteration": 0,

            # OUTPUTS
            "final_response": None,
            "used_agents": [],
            "agent_outputs": {},

            # HISTORY
            "chat_history": history,
        }

        # =====================================================
        # RUN GRAPH
        # =====================================================

        result = await graph.ainvoke(initial_state)

        # =====================================================
        # RESPONSE
        # =====================================================

        return HealthcareResponse(
            request_id=request_id,
            run_id=run_id,
            status="success",
            final_response=result.get("final_response", "No response generated."),
            validator=result.get("validation_result"),
            task_outputs=result.get("agent_outputs"),
        )

    except Exception as exc:

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail={
                "request_id": request_id,
                "run_id": run_id,
                "status": "error",
                "message": str(exc),
            },
        )


# =========================================================
# DEBUG ENDPOINT
# =========================================================

@app.post("/debug")
async def debug_workflow(
    user_query: str = Form(...),
    run_id: Optional[str] = Form(None),
):

    request_id = str(uuid.uuid4())
    run_id = run_id or str(uuid.uuid4())

    try:

        history = get_chat_history(run_id=run_id, limit=6)

        messages = history + [
            {"role": "user", "content": user_query}
        ]

        initial_state = {
            "run_id": run_id,
            "user_query": user_query,
            "messages": messages,

            "uploaded_file_path": None,
            "uploaded_file_type": None,
            "uploaded_file_mime_type": None,

            "supervisor_output": None,
            "validation_result": None,
            "validation_risk_level": None,
            "is_valid": False,
            "iteration": 0,

            "final_response": None,
            "used_agents": [],
            "agent_outputs": {},

            "chat_history": history,
        }

        result = await graph.ainvoke(initial_state)

        return {
            "request_id": request_id,
            "run_id": run_id,
            "status": "success",
            "graph_output": result,
        }

    except Exception as exc:

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# =========================================================
# CHAT HISTORY
# =========================================================

@app.get("/history/{run_id}")
async def fetch_chat_history(run_id: str):

    try:
        history = get_chat_history(run_id=run_id, limit=50)

        return {
            "run_id": run_id,
            "history": history,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )