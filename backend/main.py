"""FastAPI web API around the naive RAG pipeline."""
import os
import re

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import rag

app = FastAPI(title="RAG app V1")

# Below this cosine similarity, a chunk is considered unrelated to the question.
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.2"))


@app.on_event("startup")
def index_on_start():
    # Index once; later runs reuse chroma_db/ (same idea as the norag_rag script).
    if rag.collection().count() == 0:
        rag.reindex_all()


# ---------- documents ----------

@app.get("/api/documents")
def documents():
    return rag.list_documents()


@app.post("/api/documents")
async def upload(file: UploadFile):
    name = os.path.basename(file.filename or "")
    if not re.fullmatch(r"[\w.\- ]+\.(md|txt)", name):
        raise HTTPException(400, "Only .md and .txt files are accepted.")
    content = await file.read()
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, "The file is not valid UTF-8 text.")
    (rag.DOCS_DIR / name).write_bytes(content)
    n = rag.index_document(name)
    if n == 0:
        rag.delete_document(name)
        raise HTTPException(400, "The file has no usable text.")
    return {"name": name, "chunks": n}


@app.delete("/api/documents/{name}")
def delete(name: str):
    if name not in rag.list_documents():
        raise HTTPException(404, "Unknown document.")
    rag.delete_document(name)
    return {"deleted": name}


# ---------- settings ----------

class Settings(BaseModel):
    chunk_size: int = Field(ge=100, le=4000)
    overlap_percent: int = Field(ge=0, le=50)
    top_k: int = Field(ge=1, le=20)


@app.get("/api/settings")
def get_settings():
    return rag.load_settings()


@app.put("/api/settings")
def put_settings(s: Settings):
    return rag.save_settings(s.model_dump())


# ---------- chunks ----------

@app.get("/api/chunks/{chunk_id:path}")
def chunk(chunk_id: str):
    c = rag.get_chunk(chunk_id)
    if not c:
        raise HTTPException(404, "Chunk not found (the index may have been rebuilt).")
    return c


# ---------- ask ----------

class Question(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    documents: list[str]


@app.post("/api/ask")
def ask(q: Question):
    """Every outcome returns a 'status' so the UI never shows a silent wrong answer."""
    sources = [d for d in q.documents if d in rag.list_documents()]
    if not sources:
        raise HTTPException(400, "Select at least one document.")

    chunks = rag.retrieve(q.question, sources, rag.load_settings()["top_k"])
    relevant = [c for c in chunks if c["score"] >= MIN_SCORE]
    if not relevant:
        return {"status": "no_relevant_context", "answer": None, "references": [], "retrieved": chunks,
                "message": "No passage in the selected documents looks related to this question."}

    if not os.getenv("LLM_API_KEY"):
        return {"status": "llm_error", "answer": None, "references": [], "retrieved": relevant,
                "message": "LLM_API_KEY is not set on the server. Retrieved passages are shown below."}
    try:
        raw = rag.generate(q.question, relevant)
    except Exception as e:  # network, quota, timeout, wrong key...
        return {"status": "llm_error", "answer": None, "references": [], "retrieved": relevant,
                "message": f"The LLM call failed: {type(e).__name__}. Retrieved passages are shown below."}

    try:
        parsed = rag.parse_answer(raw)
    except (rag.ValidationError, ValueError):
        return {"status": "invalid_llm_output", "answer": None, "references": [], "retrieved": relevant,
                "message": "The LLM returned an answer that does not match the expected format.", "raw": raw}

    # A citation only counts if it points to a chunk we actually retrieved.
    by_id = {c["id"]: c for c in relevant}
    refs = [by_id[c] for c in dict.fromkeys(parsed.citations) if c in by_id]
    invented = [c for c in parsed.citations if c not in by_id]

    if not parsed.answerable:
        status = "not_in_documents"
    elif not refs:
        status = "unsupported_answer"  # answered, but cited nothing we retrieved
    else:
        status = "ok"
    return {"status": status, "answer": parsed.answer, "references": refs, "retrieved": relevant,
            "invented_citations": invented}


# ---------- frontend ----------

STATIC = rag.ROOT / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")
