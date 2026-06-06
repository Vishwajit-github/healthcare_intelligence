import os
import ssl
from pathlib import Path

import httpx
import truststore
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from openai import OpenAI

# --------------------------------------------------
# ENV
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BASE_DIR / ".env.example")


# --------------------------------------------------
# CONFIG
# --------------------------------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

OPENAI_BASE_URL = os.getenv(
    "OPENAI_BASE_URL",
    "https://api.core42.ai/v1"
)

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5.1"
)

DEFAULT_MODEL="gpt-5.1"


def _trusted_http_client() -> httpx.Client:
    return httpx.Client(
        verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
    )


def _trusted_async_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
    )


# --------------------------------------------------
# MAIN LLM
# --------------------------------------------------

model = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
    model=OPENAI_MODEL,
    temperature=0,
    http_client=_trusted_http_client(),
    http_async_client=_trusted_async_http_client(),
)


# Optional alias
llm = model


# --------------------------------------------------
# EMBEDDINGS
# --------------------------------------------------

embeddings = OpenAIEmbeddings(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
    model=os.getenv(
        "OPENAI_EMBEDDING_MODEL",
        "text-embedding-3-large"
    ),
    http_client=_trusted_http_client(),
    http_async_client=_trusted_async_http_client(),
)


# --------------------------------------------------
# 🔥 RAW OPENAI CLIENT (MOVE HERE)
# --------------------------------------------------

openai_client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
    http_client=_trusted_http_client(),
)

# --------------------------------------------------
# LOGS
# --------------------------------------------------

LOG_DIR = BASE_DIR / "logs"