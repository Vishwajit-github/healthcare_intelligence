# run.py (enhanced version)

import uvicorn
from app import app

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("   Healthcare Multi-Agent System Starting")
    print("   Port: 8000")
    print("=" * 60 + "\n")

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )