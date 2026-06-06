from langchain_community.vectorstores import Chroma
from langchain_core.tools import tool

from pathlib import Path
from threading import Lock

from config import embeddings


# =========================================================
# CONFIG
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "data" / "vector_dbs" / "medicine_vector_db"
_VECTOR_DB_BUILD_LOCK = Lock()


def _is_vector_db_ready() -> bool:
    return (DB_PATH / "chroma.sqlite3").exists() and any(DB_PATH.glob("*/data_level0.bin"))


def _ensure_vector_db() -> None:
    if _is_vector_db_ready():
        return

    with _VECTOR_DB_BUILD_LOCK:
        if _is_vector_db_ready():
            return

        from scripts.build_medicine_vector_db import build_medicine_vector_db

        print("Medicine vector database missing. Building it now...")
        build_medicine_vector_db(clean_db=True)


def _get_vectorstore() -> Chroma:
    _ensure_vector_db()

    if not _is_vector_db_ready():
        raise FileNotFoundError(
            f"Medicine vector database not found at {DB_PATH}. "
            "Run scripts/build_medicine_vector_db.py first."
        )

    vectorstore = Chroma(
        persist_directory=str(DB_PATH),
        embedding_function=embeddings,
    )

    if vectorstore._collection.count() == 0:
        raise ValueError(
            f"Medicine vector database at {DB_PATH} is empty. "
            "Rebuild it with scripts/build_medicine_vector_db.py."
        )

    return vectorstore


# =========================================================
# TOOL
# =========================================================

@tool
def medicine_retrieval_tool(query: str) -> str:
    """
    Retrieve medicine records from the medicine knowledge base using
    semantic vector search.

    PURPOSE:
    This tool searches a curated medicine database containing medicine
    names, compositions, uses, side effects, dosage information,
    manufacturer details, safety information, and product metadata.

    WHEN TO USE:
    - User asks about a medicine.
    - User wants medicines for a symptom or condition.
    - User asks for medicines with a specific composition.
    - User asks for side effects of medicines.
    - User asks for alternative medicines.
    - User asks for medicine brand information.
    - User asks which medicines are used for a disease.
    - User asks to compare medicines.
    - User asks about ingredients in medicines.
    - User asks about available cough, fever, allergy, pain,
      cold, infection, gastric, or similar medications.

    WHEN NOT TO USE:
    - General medical diagnosis questions.
    - Emergency medical situations.
    - Questions unrelated to medicines.
    - Legal, financial, technical, or non-healthcare queries.

    SEARCH STRATEGY:
    - Performs semantic similarity search using vector embeddings.
    - Retrieves the 15 most relevant medicine records.
    - Returns complete medicine entries exactly as stored.
    - Results may include medicine name, composition, uses,
      side effects, image URL, manufacturer, and other metadata.

    INPUT:
    query: Natural language medicine-related question.

    OUTPUT:
    String containing the top 15 retrieved medicine records,
    ordered by semantic relevance.

    EXAMPLES:
    - "dry cough medicines"
    - "medicine containing paracetamol"
    - "side effects of cetirizine"
    - "best medicines for fever"
    - "cough syrup for adults"
    - "medicines used for allergic rhinitis"
    """

    vectorstore = _get_vectorstore()
    docs = vectorstore.similarity_search(
        query=query,
        k=10,
    )

    if not docs:
        return "No relevant medicines found."

    results = []

    for idx, doc in enumerate(docs, start=1):
        results.append(
            f"""
==============================
RESULT {idx}
==============================
{doc.page_content}
"""
        )

    return "\n".join(results)