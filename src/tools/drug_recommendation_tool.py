import csv
import math
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return None

try:
    from langchain_community.tools import tool
except ImportError:
    def tool(fn):
        return fn

try:
    from langchain_openai import OpenAIEmbeddings
except ImportError:
    OpenAIEmbeddings = None


load_dotenv(Path(__file__).resolve().parents[2] / ".env.example")


MEDICINE_DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "medicine_data"
    / "Medicine_Details.csv"
)
EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_SEARCH_COLUMN = "Uses"
SUPPORTED_SEARCH_COLUMNS = {
    "uses": "Uses",
    "condition": "Uses",
    "conditions": "Uses",
    "symptom": "Uses",
    "symptoms": "Uses",
    "medicine": "Medicine Name",
    "medicine_name": "Medicine Name",
    "drug": "Medicine Name",
    "composition": "Composition",
    "ingredient": "Composition",
    "side_effects": "Side_effects",
}
_EMBEDDINGS_CLIENT: Optional[object] = None
_EMBEDDING_CACHE: Dict[Tuple[str, str], List[float]] = {}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "have",
    "with",
    "the",
    "this",
    "that",
    "treatment",
    "of",
    "in",
    "to",
    "due",
    "is",
    "my",
    "i",
}


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def _query_tokens(query: str) -> List[str]:
    normalized_query = _normalize_text(query)
    return [
        token
        for token in normalized_query.split()
        if len(token) > 2 and token not in STOPWORDS
    ]


def _parse_percent(value: str) -> float:
    if value is None:
        return 0.0

    cleaned_value = str(value).replace("%", "").strip()
    try:
        return float(cleaned_value)
    except ValueError:
        return 0.0


def _load_medicines(data_path: Path = MEDICINE_DATA_PATH) -> List[Dict[str, str]]:
    with data_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def _resolve_search_column(search_column: str) -> str:
    requested_column = (search_column or DEFAULT_SEARCH_COLUMN).strip()
    normalized_column = requested_column.lower().replace(" ", "_")
    return SUPPORTED_SEARCH_COLUMNS.get(normalized_column, requested_column)


def _get_embeddings_client() -> object:
    global _EMBEDDINGS_CLIENT

    if _EMBEDDINGS_CLIENT is None:
        if OpenAIEmbeddings is not None:
            _EMBEDDINGS_CLIENT = OpenAIEmbeddings(
                model=EMBEDDING_MODEL,
                api_key=os.getenv("OPENAI_API_KEY"),
            )
        else:
            from openai import OpenAI

            _EMBEDDINGS_CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    return _EMBEDDINGS_CLIENT


def _client_embed_query(text: str) -> List[float]:
    embeddings_client = _get_embeddings_client()

    if hasattr(embeddings_client, "embed_query"):
        return embeddings_client.embed_query(text)

    response = embeddings_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def _client_embed_documents(texts: List[str]) -> List[List[float]]:
    embeddings_client = _get_embeddings_client()

    if hasattr(embeddings_client, "embed_documents"):
        return embeddings_client.embed_documents(texts)

    response = embeddings_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def _cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def _embed_text(text: str) -> List[float]:
    cache_key = ("query", text)
    if cache_key not in _EMBEDDING_CACHE:
        _EMBEDDING_CACHE[cache_key] = _client_embed_query(text)

    return _EMBEDDING_CACHE[cache_key]


def _embed_documents(texts: List[str]) -> Dict[str, List[float]]:
    missing_texts = [
        text
        for text in texts
        if ("document", text) not in _EMBEDDING_CACHE
    ]

    if missing_texts:
        embeddings = _client_embed_documents(missing_texts)
        for text, embedding in zip(missing_texts, embeddings):
            _EMBEDDING_CACHE[("document", text)] = embedding

    return {
        text: _EMBEDDING_CACHE[("document", text)]
        for text in texts
    }


def _semantic_search_rows(
    query: str,
    rows: List[Dict[str, str]],
    search_column: str,
    top_k: int,
) -> List[Dict[str, str]]:
    column_values = [
        (index, (row.get(search_column) or "").strip())
        for index, row in enumerate(rows)
    ]
    column_values = [
        (index, value)
        for index, value in column_values
        if value
    ]

    unique_values = sorted({value for _, value in column_values})
    document_embeddings = _embed_documents(unique_values)
    query_embedding = _embed_text(query)

    scored_rows = []
    for row_index, column_value in column_values:
        similarity_score = _cosine_similarity(
            query_embedding,
            document_embeddings[column_value],
        )
        row = rows[row_index].copy()
        row["_source_index"] = row_index
        row["_similarity_score"] = similarity_score
        scored_rows.append(row)

    scored_rows.sort(key=lambda row: row["_similarity_score"], reverse=True)
    return scored_rows[: max(1, top_k)]


def _match_score(row: Dict[str, str], query: str, tokens: List[str]) -> int:
    uses = _normalize_text(row.get("Uses", ""))
    medicine_name = _normalize_text(row.get("Medicine Name", ""))
    composition = _normalize_text(row.get("Composition", ""))
    normalized_query = _normalize_text(query)

    score = 0

    if normalized_query and normalized_query in uses:
        score += 100

    score += sum(12 for token in tokens if token in uses.split())
    score += sum(4 for token in tokens if token in medicine_name.split())
    score += sum(3 for token in tokens if token in composition.split())

    return score


def _format_recommendation(rank: int, row: Dict[str, str]) -> str:
    similarity = row.get("_similarity_score")
    similarity_line = ""
    if isinstance(similarity, float):
        similarity_line = f"\n- Semantic similarity: {similarity:.3f}"

    return f"""
Rank {rank}: {row.get("Medicine Name", "Unknown")}
- Composition: {row.get("Composition", "NA")}
- Associated use: {row.get("Uses", "NA")}
- Review ranking: Excellent {row.get("Excellent Review %", "0")}%, Average {row.get("Average Review %", "0")}%, Poor {row.get("Poor Review %", "0")}%
- Source row index: {row.get("_source_index", "NA")}{similarity_line}
- Manufacturer: {row.get("Manufacturer", "NA")}
- Side effects: {row.get("Side_effects", "NA")}
- Image URL: {row.get("Image URL", "NA")}
""".strip()


def _truncate_value(value, max_length: int = 120) -> str:
    text = str(value or "").replace("\n", " ").strip()
    if len(text) <= max_length:
        return text

    return f"{text[: max_length - 3]}..."


def _format_recommendations_dataframe(rows: List[Dict[str, str]]) -> str:
    table_rows = []

    for index, row in enumerate(rows, start=1):
        similarity = row.get("_similarity_score")
        table_rows.append(
            {
                "rank": index,
                "medicine_name": row.get("Medicine Name", "NA"),
                "composition": _truncate_value(row.get("Composition", "NA")),
                "uses": _truncate_value(row.get("Uses", "NA")),
                "excellent_review_%": row.get("Excellent Review %", "0"),
                "average_review_%": row.get("Average Review %", "0"),
                "poor_review_%": row.get("Poor Review %", "0"),
                "manufacturer": _truncate_value(row.get("Manufacturer", "NA"), 80),
                "side_effects": _truncate_value(row.get("Side_effects", "NA")),
                "source_row_index": row.get("_source_index", "NA"),
                "semantic_similarity": (
                    round(similarity, 3)
                    if isinstance(similarity, float)
                    else "NA"
                ),
            }
        )

    if pd is not None:
        return pd.DataFrame(table_rows).to_string(index=False)

    if not table_rows:
        return ""

    headers = list(table_rows[0].keys())
    lines = [" | ".join(headers)]
    lines.append(" | ".join("-" * len(header) for header in headers))

    for table_row in table_rows:
        lines.append(" | ".join(str(table_row[header]) for header in headers))

    return "\n".join(lines)


def drug_recommendation_tool(
    symptoms_or_condition: str,
    top_n: int = 5,
    search_column: str = DEFAULT_SEARCH_COLUMN,
    semantic_top_k: int = 5,
    use_embeddings: bool = True,
    data_path: Optional[str] = None,
) -> str:
    """
    Recommend medicines associated with symptoms or health conditions.

    The tool first performs semantic similarity search over one structured data
    column, defaulting to Uses for symptoms and health conditions. It then ranks
    the semantically matched medicines by Excellent Review %, then Average
    Review %, then lower Poor Review %.

    Args:
        symptoms_or_condition: Symptoms or health condition to search for.
        top_n: Number of ranked medicines to return.
        search_column: CSV column to embed/search. Defaults to Uses.
        semantic_top_k: Number of nearest rows to fetch before review ranking.
        use_embeddings: Use OpenAI embeddings for semantic search when True.
        data_path: Optional custom path to a medicine CSV with review columns.

    Returns:
        Ranked medicine recommendations with review percentages and safety notes.
    """
    query = symptoms_or_condition.strip()
    if not query:
        return "Error: symptoms_or_condition input is required."

    medicine_data_path = Path(data_path).expanduser() if data_path else MEDICINE_DATA_PATH
    tokens = _query_tokens(query)
    resolved_search_column = _resolve_search_column(search_column)

    if not tokens:
        return "Error: please provide a more specific symptom or health condition."

    try:
        rows = _load_medicines(medicine_data_path)
    except Exception as exc:
        return f"Error loading medicine data: {exc}"

    if rows and resolved_search_column not in rows[0]:
        return (
            f"Error: search column '{resolved_search_column}' not found in medicine data. "
            f"Available columns: {', '.join(rows[0].keys())}"
        )

    matches = []
    semantic_status = (
        "OpenAI embeddings semantic search"
        if use_embeddings
        else "keyword search because embedding search is disabled"
    )

    if use_embeddings:
        try:
            matches = _semantic_search_rows(
                query=query,
                rows=rows,
                search_column=resolved_search_column,
                top_k=semantic_top_k,
            )
        except Exception as exc:
            semantic_status = f"keyword fallback because embedding search failed: {exc}"

    if not matches:
        for row_index, row in enumerate(rows):
            match_score = _match_score(row, query, tokens)
            if match_score <= 0:
                continue

            row = row.copy()
            row["_source_index"] = row_index
            row["_match_score"] = match_score
            matches.append(row)

    for row in matches:
        row["_match_score"] = row.get("_match_score") or _match_score(row, query, tokens)
        row["_excellent_review"] = _parse_percent(row.get("Excellent Review %", "0"))
        row["_average_review"] = _parse_percent(row.get("Average Review %", "0"))
        row["_poor_review"] = _parse_percent(row.get("Poor Review %", "0"))

    if not matches:
        return (
            f"No medicine recommendations found for '{query}'. Try a different "
            "symptom or condition term from the medicine uses data."
        )

    candidate_selection = (
        f"top {semantic_top_k} semantically nearest rows, then rank candidates"
        if use_embeddings and matches and "_similarity_score" in matches[0]
        else "keyword-matched rows, then rank candidates"
    )

    matches.sort(
        key=lambda row: (
            row["_excellent_review"],
            row["_average_review"],
            -row["_poor_review"],
            row.get("_similarity_score", 0.0),
            row["_match_score"],
        ),
        reverse=True,
    )

    selected_matches = matches[: max(1, top_n)]
    recommendations_table = _format_recommendations_dataframe(selected_matches)

    return f"""
Drug recommendations for: {query}
Search method: {semantic_status}
Search column: {resolved_search_column}
Candidate selection: {candidate_selection}.
Ranking method: Excellent Review %, Average Review %, lower Poor Review %, semantic similarity, then text relevance.

{recommendations_table}

Tool usage note: These table rows are dataset-based suggestions only. The agent
may use web search when available and its own expert medical knowledge to add
real-world context, safety considerations, and clinical judgment around these
options.

Safety note: These are data-driven medicine recommendations, not a prescription.
Confirm suitability, dosage, contraindications, allergies, pregnancy risk, and
drug interactions with a licensed clinician or pharmacist.
""".strip()


@tool
def recommend_drugs_for_condition(
    symptoms_or_condition: str,
    top_n: int = 5,
    search_column: str = DEFAULT_SEARCH_COLUMN,
) -> str:
    """
    Recommend ranked medicines for symptoms or a health condition.

    Input:
    - symptoms_or_condition: Symptoms or condition, for example "cough with mucus",
      "bacterial infection", "acid reflux", or "allergic conditions".
    - top_n: Number of ranked recommendations to return.
    - search_column: Column to use for embedding similarity. Use "Uses" for
      symptoms or conditions.
    """
    print("Entering in Medicine Recommendation tool")
    recommended_drugs=drug_recommendation_tool(
        symptoms_or_condition=symptoms_or_condition,
        top_n=top_n,
        search_column=search_column,
    )

    print(f"Drug Recommendation Output {recommended_drugs}")
    return recommended_drugs
