import os
import re
import shutil
import ssl
import sys
from pathlib import Path
from typing import Dict, List

import httpx
import truststore
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env.example")


def trusted_http_client() -> httpx.Client:
    return httpx.Client(
        verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
    )


def trusted_async_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
    )


embeddings = OpenAIEmbeddings(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.core42.ai/v1"),
    model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"),
    http_client=trusted_http_client(),
    http_async_client=trusted_async_http_client(),
)


# =========================================================
# PATH SETUP
# =========================================================
DATA_PATH = ROOT_DIR / "data/medicine_data/medicine_details_embedding_corpus.txt"
DB_PATH = ROOT_DIR / "data/vector_dbs/medicine_vector_db"
RECORDS_PER_VECTOR_CHUNK = 5


def extract_metadata(block: str, record_index: int) -> Dict[str, str]:
    metadata: Dict[str, str] = {
        "source": DATA_PATH.name,
        "file_path": str(DATA_PATH),
        "record_index": str(record_index),
    }

    for line in block.splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        normalized_key = key.strip().lower().replace(" ", "_").replace("%", "percent")
        metadata[normalized_key] = value.strip()

    return metadata


def build_chunk_metadata(blocks: List[str], start_index: int) -> Dict[str, str]:
    metadata = {
        "source": DATA_PATH.name,
        "file_path": str(DATA_PATH),
        "record_start_index": str(start_index),
        "record_end_index": str(start_index + len(blocks) - 1),
        "record_count": str(len(blocks)),
    }

    first_record_metadata = extract_metadata(blocks[0], start_index)
    for key in ("medicine_name", "composition", "uses"):
        if key in first_record_metadata:
            metadata[f"first_{key}"] = first_record_metadata[key]

    return metadata


def is_medicine_vector_db_ready() -> bool:
    return (DB_PATH / "chroma.sqlite3").exists() and any(DB_PATH.glob("*/data_level0.bin"))


def load_medicine_documents() -> List[Document]:
    print("\nLoading medicine corpus from:", DATA_PATH)

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Medicine corpus not found: {DATA_PATH}")

    raw_text = DATA_PATH.read_text(encoding="utf-8")
    medicine_blocks = [
        block.strip()
        for block in re.split(r"\n\s*\n", raw_text)
        if block.strip()
    ]

    if len(medicine_blocks) == 0:
        raise ValueError("No medicine records found. Check the corpus formatting.")

    documents = []
    for start_index in range(0, len(medicine_blocks), RECORDS_PER_VECTOR_CHUNK):
        chunk_blocks = medicine_blocks[start_index:start_index + RECORDS_PER_VECTOR_CHUNK]
        documents.append(
            Document(
                page_content="\n\n".join(chunk_blocks),
                metadata=build_chunk_metadata(chunk_blocks, start_index),
            )
        )

    print(f"Total medicine records loaded: {len(medicine_blocks)}")
    print(f"Records per vector chunk: {RECORDS_PER_VECTOR_CHUNK}")
    print(f"Total vector chunks created: {len(documents)}")
    return documents


def build_medicine_vector_db(clean_db: bool = False) -> Path:
    if is_medicine_vector_db_ready() and not clean_db:
        print("Medicine vector DB already exists at:", DB_PATH)
        return DB_PATH

    if DB_PATH.exists():
        print("Removing old or incomplete medicine vector DB...")
        shutil.rmtree(DB_PATH)

    documents = load_medicine_documents()

    print("\nThis will take around 3 minutes, please wait.")
    print("\nCreating medicine vector database...")
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=str(DB_PATH),
    )

    try:
        vectorstore.persist()
    except Exception:
        pass

    print("\nMEDICINE VECTOR DB BUILD COMPLETE")
    print("Location:", DB_PATH)
    print("Embeddings model:", getattr(embeddings, "model", "unknown"))
    print("Total medicine records indexed:", len(documents))
    return DB_PATH


if __name__ == "__main__":
    build_medicine_vector_db(clean_db=True)
