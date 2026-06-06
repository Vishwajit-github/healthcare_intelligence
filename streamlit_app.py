import json
import uuid
from typing import Any

import requests
import streamlit as st


DEFAULT_API_BASE_URL = "http://localhost:8000"


def build_run_id() -> str:
    return f"streamlit-{uuid.uuid4()}"


def api_get(api_base_url: str, path: str) -> dict[str, Any]:
    response = requests.get(f"{api_base_url.rstrip('/')}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def call_healthcare_api(
    api_base_url: str,
    user_query: str,
    run_id: str | None,
    uploaded_file,
) -> dict[str, Any]:
    data = {
        "user_query": user_query,
    }

    if run_id:
        data["run_id"] = run_id

    files = None
    if uploaded_file is not None:
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type or "application/octet-stream",
            )
        }

    response = requests.post(
        f"{api_base_url.rstrip('/')}/run",
        data=data,
        files=files,
        timeout=600,
    )

    try:
        body = response.json()
    except Exception:
        body = {
            "raw_response": response.text,
        }

    if response.status_code >= 400:
        return {
            "status": "error",
            "status_code": response.status_code,
            "error_response": body,
        }

    return body


def render_agent_outputs(task_outputs: Any) -> None:
    if not task_outputs:
        st.info("No specialist agent outputs were returned.")
        return

    if not isinstance(task_outputs, dict):
        st.json(task_outputs)
        return

    for agent_name, output in task_outputs.items():
        with st.expander(agent_name, expanded=False):
            if isinstance(output, dict):
                action = output.get("action")
                if action:
                    st.caption(f"Action: {action}")

                if output.get("output"):
                    st.markdown("**Output**")
                    st.write(output["output"])

                with st.expander("Raw agent trace", expanded=False):
                    st.json(output)
            else:
                st.write(output)


def render_validator(validator: Any) -> None:
    if not validator:
        return

    with st.expander("Validator Result", expanded=False):
        if isinstance(validator, dict):
            is_valid = validator.get("is_valid")
            risk_level = validator.get("risk_level")

            if is_valid is not None:
                st.caption(f"Valid: {is_valid}")
            if risk_level:
                st.caption(f"Risk level: {risk_level}")

            reason = validator.get("reason")
            if reason:
                st.write(reason)

            st.json(validator)
        else:
            st.write(validator)


st.set_page_config(
    page_title="Healthcare AI",
    page_icon="H",
    layout="wide",
)

st.title("Healthcare Multi-Agent AI")
st.caption(
    "FastAPI + LangGraph clinical decision support for symptoms, risk, "
    "diagnostics, labs, imaging, medications, vitals, and clinical documents."
)

with st.sidebar:
    st.header("API Settings")
    api_base_url = st.text_input(
        "FastAPI base URL",
        value=DEFAULT_API_BASE_URL,
        help="Run `python run.py` first so the API is available on port 8000.",
    )

    if st.button("Check API Health"):
        try:
            st.success(api_get(api_base_url, "/health"))
        except Exception as exc:
            st.error(f"API health check failed: {exc}")

    st.divider()
    st.header("Session")
    if "run_id" not in st.session_state:
        st.session_state.run_id = build_run_id()

    run_id = st.text_input(
        "run_id",
        value=st.session_state.run_id,
        help="Reuse this value for follow-up questions in the same session.",
    )
    st.session_state.run_id = run_id

    if st.button("New Session"):
        st.session_state.run_id = build_run_id()
        st.rerun()

st.subheader("Ask a Healthcare Question")

user_query = st.text_area(
    "User question",
    height=220,
    placeholder=(
        "Example: Patient has fever, cough, low oxygen saturation, and elevated "
        "CRP. Provide a cautious clinical interpretation and escalation guidance."
    ),
)

uploaded_file = st.file_uploader(
    "Optional medical file",
    type=["pdf", "doc", "docx", "txt", "png", "jpg", "jpeg", "webp"],
    help="The API stores uploaded files under `uploads/` and passes their path to the graph state.",
)

col_submit, col_clear = st.columns([1, 4])

with col_submit:
    submit = st.button("Run Healthcare AI", type="primary", use_container_width=True)

with col_clear:
    if st.button("Clear Last Response"):
        st.session_state.pop("last_response", None)
        st.rerun()

if submit:
    if not user_query.strip():
        st.warning("Please enter a healthcare query.")
    else:
        with st.spinner("Running healthcare multi-agent workflow..."):
            try:
                st.session_state.last_response = call_healthcare_api(
                    api_base_url=api_base_url,
                    user_query=user_query.strip(),
                    run_id=run_id.strip() or None,
                    uploaded_file=uploaded_file,
                )
            except requests.exceptions.ConnectionError:
                st.error(
                    "Could not connect to the FastAPI server. Start it with `python run.py`."
                )
            except Exception as exc:
                st.error(f"Request failed: {exc}")

response = st.session_state.get("last_response")

if response:
    if response.get("status") == "error":
        st.error("API returned an error.")
        st.json(response)
    else:
        st.divider()
        st.write(response.get("final_response", "No final response returned."))

        render_validator(response.get("validator"))

        st.subheader("Specialist Agent Outputs")
        render_agent_outputs(response.get("task_outputs"))

        with st.expander("Raw API Response", expanded=False):
            st.code(json.dumps(response, indent=2, ensure_ascii=False), language="json")
