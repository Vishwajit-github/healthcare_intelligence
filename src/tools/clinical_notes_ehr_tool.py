import pymupdf
import base64
import numpy as np
import faiss
import tiktoken

from typing import List
from openai import OpenAI
from langchain_community.tools import tool

from config import model, embeddings, openai_client


# =========================================================
# CONFIG
# =========================================================

client = openai_client

MODEL_NAME = model
EMBED_MODEL = "text-embedding-3-large"

CHUNK_SIZE = 1200
TOP_K = 5
TOKEN_THRESHOLD = 7000

enc = tiktoken.get_encoding("cl100k_base")


# =========================================================
# PAGE → IMAGE
# =========================================================

def page_to_base64(page):
    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
    return base64.b64encode(pix.tobytes("png")).decode()


# =========================================================
# STRUCTURE DETECTION
# =========================================================

def detect_structure(doc):

    content = [{
        "type": "text",
        "text": """
Classify this PDF as:

STRUCTURED / UNSTRUCTURED

STRUCTURED:
- clean digital text
- reports
- paragraphs

UNSTRUCTURED:
- tables
- forms
- columns
- scanned-like pages
"""
    }]

    for i in range(min(2, len(doc))):
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{page_to_base64(doc[i])}"
            }
        })

    resp = openai_client.chat.completions.create(
        model="gpt-5.1",
        temperature=0,
        messages=[{"role": "user", "content": content}],
    )

    return resp.choices[0].message.content.strip().upper()


# =========================================================
# OCR PAGE EXTRACTION
# =========================================================

def extract_page_llm(page):

    img = page_to_base64(page)

    resp = openai_client.chat.completions.create(
        model="gpt-5.1",
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all readable text from this medical page. Preserve structure."
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img}"}
                    }
                ],
            }
        ],
    )

    return resp.choices[0].message.content.strip()


# =========================================================
# TOKEN HELPERS
# =========================================================

def count_tokens(text: str) -> int:
    return len(enc.encode(text))


def chunk_text(text: str) -> List[str]:
    tokens = enc.encode(text)
    return [
        enc.decode(tokens[i:i + CHUNK_SIZE])
        for i in range(0, len(tokens), CHUNK_SIZE)
    ]


# =========================================================
# EMBEDDINGS + FAISS
# =========================================================

def embed(texts: List[str]):
    return client.embeddings.create(
        model=EMBED_MODEL,
        input=texts
    ).data


def embed_query(q: str):
    return client.embeddings.create(
        model=EMBED_MODEL,
        input=[q]
    ).data[0].embedding


def build_index(vectors):
    arr = np.array([v.embedding for v in vectors]).astype("float32")
    index = faiss.IndexFlatL2(arr.shape[1])
    index.add(arr)
    return index


def retrieve(index, chunks, q_vec):
    _, I = index.search(np.array([q_vec]).astype("float32"), TOP_K)
    return [chunks[i] for i in I[0] if i < len(chunks)]


# =========================================================
# DIRECT ANSWER
# =========================================================

def answer_direct(question: str, doc: str):

    resp = openai_client.chat.completions.create(
        model="gpt-5.1",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "Answer only using the document. If not found say 'Not found in document'."
            },
            {
                "role": "user",
                "content": f"""
DOCUMENT:
{doc}

QUESTION:
{question}
"""
            }
        ],
    )

    return resp.choices[0].message.content


# =========================================================
# RAG ANSWER
# =========================================================

def answer_rag(question: str, chunks: List[str]):

    context = "\n\n---\n\n".join(chunks)

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "Use only provided context. Do not hallucinate."
            },
            {
                "role": "user",
                "content": f"""
CONTEXT:
{context}

QUESTION:
{question}
"""
            }
        ],
    )

    return resp.choices[0].message.content


# =========================================================
# MAIN PIPELINE
# =========================================================
def process_pdf(pdf_path: str, question: str):

    print("\n" + "="*80)
    print(f"[START] Processing PDF: {pdf_path}")
    print("="*80)

    doc = pymupdf.open(pdf_path)

    print(f"[INFO] Pages in document: {len(doc)}")

    if len(doc) == 0:
        print("[ERROR] Empty PDF")
        return "Empty PDF"

    # -----------------------------------------------------
    # STEP 1: STRUCTURE DETECTION
    # -----------------------------------------------------

    print("\n[STEP 1] Detecting structure...")

    try:
        structure = detect_structure(doc)
        print(f"[STRUCTURE RESULT] {structure}")
    except Exception as e:
        print(f"[ERROR] Structure detection failed: {e}")
        return str(e)

    use_ocr = "UNSTRUCTURED" in structure or "SCANNED" in structure

    print(f"[DECISION] use_ocr = {use_ocr}")

    # -----------------------------------------------------
    # STEP 2: EXTRACTION
    # -----------------------------------------------------

    print("\n[STEP 2] Extracting text page-by-page...")

    full_text = ""

    for i, page in enumerate(doc):

        print(f"\n--- PAGE {i+1}/{len(doc)} ---")

        try:
            text = page.get_text().strip()
            print(f"[PyMuPDF text length] {len(text)}")

            if len(text) < 30:
                print("[MODE] OCR fallback (short text)")
                text = extract_page_llm(page)

            elif use_ocr:
                print("[MODE] OCR forced (unstructured doc)")
                text = extract_page_llm(page)

            else:
                print("[MODE] PyMuPDF used")

            print(f"[PAGE TEXT SAMPLE] {text[:200]}")

        except Exception as e:
            print(f"[ERROR] Page extraction failed: {e}")
            text = ""

        full_text += text + "\n"

    doc.close()

    print("\n[INFO] Full text length:", len(full_text))

    if len(full_text.strip()) < 50:
        print("[ERROR] No meaningful text extracted")
        return "No meaningful text extracted"

    # -----------------------------------------------------
    # STEP 3: DIRECT vs RAG
    # -----------------------------------------------------

    token_count = count_tokens(full_text)
    print(f"\n[STEP 3] Token count: {token_count}")
    print(f"[TOKEN THRESHOLD] {TOKEN_THRESHOLD}")

    if token_count <= TOKEN_THRESHOLD:

        print("[MODE] DIRECT ANSWER (no RAG)")
        result = answer_direct(question, full_text)

        print("[DONE] Direct answer generated")
        return result

    # -----------------------------------------------------
    # STEP 4: CHUNKING + RETRIEVAL
    # -----------------------------------------------------

    print("\n[STEP 4] Chunking document...")

    chunks = chunk_text(full_text)
    print(f"[INFO] Total chunks: {len(chunks)}")

    print("\n[STEP 5] Embedding chunks...")

    vectors = embed(chunks)
    print("[INFO] Embeddings created")

    print("[STEP 6] Building FAISS index...")

    index = build_index(vectors)

    print("[STEP 7] Embedding query...")

    q_vec = embed_query(question)

    print("[STEP 8] Retrieving top chunks...")

    top_chunks = retrieve(index, chunks, q_vec)

    print(f"[TOP K] Retrieved {len(top_chunks)} chunks")

    for i, c in enumerate(top_chunks):
        print(f"\n--- TOP CHUNK {i+1} ---")
        print(c[:300])

    # -----------------------------------------------------
    # STEP 5: FINAL ANSWER
    # -----------------------------------------------------

    print("\n[STEP 9] Generating final answer (RAG)...")

    result = answer_rag(question, top_chunks)

    print("[DONE] RAG answer generated")

    return result
# =========================================================
# LANGCHAIN TOOL
# =========================================================

def pdf_medical_rag_tool(pdf_path: str, user_question: str) -> str:
    """
    End-to-end Medical PDF QA Tool:

    Flow:
    1. PDF load
    2. structure detection
    3. PyMuPDF + OCR hybrid extraction
    4. token check
    5. direct LLM OR RAG (FAISS top-5)
    6. final answer
    """

    try:
        return process_pdf(pdf_path, user_question)
    except Exception as e:
        return f"Error: {str(e)}"