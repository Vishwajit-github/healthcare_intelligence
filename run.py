# run.py (enhanced version)

import uvicorn
from app import app
from scripts.build_medicine_vector_db import (
    build_medicine_vector_db,
    is_medicine_vector_db_ready,
)


def ensure_medicine_vector_db() -> None:
    if is_medicine_vector_db_ready():
        print("Medicine vector database found. Skipping rebuild.")
        return

    print("Medicine vector database not found. Building it before startup...")
    build_medicine_vector_db(clean_db=True)

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("   Healthcare Multi-Agent System Starting")
    print("   Port: 8000")
    print("=" * 60 + "\n")

    ensure_medicine_vector_db()

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )