"""Naive RAG pipeline: chunking, indexing, retrieval, grounded generation.

Phase 1 (indexing):  document -> chunks -> embeddings -> ChromaDB
Phase 2 (answering): question -> embedding -> top-k chunks -> LLM -> validated answer
"""
import json
import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DOCS_DIR = Path(os.getenv("DOCS_DIR", ROOT / "corpus"))
DB_DIR = Path(os.getenv("DB_DIR", ROOT / "chroma_db"))
SETTINGS_FILE = DB_DIR / "settings.json"
COLLECTION = "chunks"

DEFAULT_SETTINGS = {"chunk_size": 800, "overlap_percent": 10, "top_k": 5}

# all-MiniLM-L6-v2 (384 dimensions), run locally through ONNX. Same model for index and query.
EMBED = DefaultEmbeddingFunction()

DB_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
client = chromadb.PersistentClient(path=str(DB_DIR))


def collection():
    return client.get_or_create_collection(
        name=COLLECTION, embedding_function=EMBED, metadata={"hnsw:space": "cosine"}
    )


# ---------- settings ----------

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        return {**DEFAULT_SETTINGS, **json.loads(SETTINGS_FILE.read_text())}
    return dict(DEFAULT_SETTINGS)


def save_settings(new: dict) -> dict:
    old = load_settings()
    merged = {**old, **new}
    SETTINGS_FILE.write_text(json.dumps(merged))
    # chunk size or overlap change the chunks themselves, so everything is re-indexed.
    # top_k only changes the query, so nothing is recomputed.
    if (merged["chunk_size"], merged["overlap_percent"]) != (old["chunk_size"], old["overlap_percent"]):
        reindex_all()
    return merged


# ---------- phase 1: indexing ----------

def chunk_text(text: str, chunk_size: int, overlap_percent: int) -> list[str]:
    """Fixed-size character windows with overlap, as in ask_rag_google.py."""
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= 20]
    text = "\n\n".join(paragraphs)
    overlap = chunk_size * overlap_percent // 100
    step = max(1, chunk_size - overlap)
    return [text[i:i + chunk_size] for i in range(0, len(text), step)]


def index_document(name: str) -> int:
    s = load_settings()
    text = (DOCS_DIR / name).read_text(encoding="utf-8", errors="replace")
    chunks = chunk_text(text, s["chunk_size"], s["overlap_percent"])
    col = collection()
    col.delete(where={"source": name})
    if not chunks:
        return 0
    ids = [f"{name}::{i}" for i in range(len(chunks))]
    metas = [{"source": name, "chunk_index": i} for i in range(len(chunks))]
    for start in range(0, len(chunks), 5000):  # Chroma limits batch size
        col.add(documents=chunks[start:start + 5000], ids=ids[start:start + 5000],
                metadatas=metas[start:start + 5000])
    return len(chunks)


def reindex_all() -> None:
    client.delete_collection(COLLECTION) if COLLECTION in [c.name for c in client.list_collections()] else None
    for name in list_documents():
        index_document(name)


def list_documents() -> list[str]:
    return sorted(p.name for p in DOCS_DIR.iterdir() if p.suffix in (".md", ".txt"))


def delete_document(name: str) -> None:
    (DOCS_DIR / name).unlink(missing_ok=True)
    collection().delete(where={"source": name})


def get_chunk(chunk_id: str) -> dict | None:
    r = collection().get(ids=[chunk_id])
    if not r["ids"]:
        return None
    return {"id": chunk_id, "text": r["documents"][0], **r["metadatas"][0]}


# ---------- phase 2: answering ----------

def retrieve(question: str, sources: list[str], top_k: int) -> list[dict]:
    col = collection()
    where = {"source": sources[0]} if len(sources) == 1 else {"source": {"$in": sources}}
    r = col.query(query_texts=[question], n_results=top_k, where=where)
    return [
        {"id": i, "text": d, "source": m["source"], "chunk_index": m["chunk_index"],
         "score": round(1 - dist, 3)}  # cosine similarity, not a confidence
        for i, d, m, dist in zip(r["ids"][0], r["documents"][0], r["metadatas"][0], r["distances"][0])
    ]


class LLMAnswer(BaseModel):
    """Schema the LLM must follow. Anything else is rejected before reaching the UI."""
    answerable: bool
    answer: str = Field(min_length=1)
    citations: list[str] = Field(default_factory=list)


PROMPT = """You answer questions using ONLY the excerpts below.
Each excerpt starts with its id in square brackets.
If the excerpts do not contain the answer, set "answerable" to false and say so in "answer".
Return ONLY a JSON object: {{"answerable": bool, "answer": string, "citations": [excerpt ids you used]}}

EXCERPTS:
{context}

QUESTION:
{question}
"""


def generate(question: str, chunks: list[dict]) -> str:
    llm = OpenAI(
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    )
    context = "\n\n".join(f"[{c['id']}]\n{c['text']}" for c in chunks)
    resp = llm.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gemini-3.5-flash-lite"),
        messages=[{"role": "user", "content": PROMPT.format(context=context, question=question)}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return resp.choices[0].message.content or ""


def parse_answer(raw: str) -> LLMAnswer:
    raw = raw.strip()
    if raw.startswith("```"):  # some models wrap JSON in a code fence
        raw = raw.strip("`").removeprefix("json").strip()
    return LLMAnswer.model_validate_json(raw)


__all__ = ["ValidationError"]
