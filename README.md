# RAG app V1 (naive RAG)

A web app where you ask a question about a document corpus and get a grounded answer,
with references to the passages it was built from. V1 is naive on purpose: it is the baseline for V2.

## Pipeline

```
Indexing (on upload / settings change)
  .md/.txt -> fixed-size character chunks (with overlap) -> all-MiniLM-L6-v2 embeddings -> ChromaDB

Answering (every question)
  question -> same embedding model -> top-k chunks (filtered to the selected documents)
           -> prompt (instructions + excerpts with ids + question) -> LLM (JSON)
           -> Pydantic validation -> keep only citations that were really retrieved -> UI
```

| File | Role |
|---|---|
| `backend/rag.py` | chunking, indexing, retrieval, LLM call, response schema |
| `backend/main.py` | FastAPI routes, controlled failures |
| `static/index.html` | UI: documents, settings, question, answer, references, chunk viewer |
| `eval/questions.json` | question set with expected answer and evidence location |
| `eval/run_eval.py` | retrieval baseline (hit rate@k, MRR) |
| `corpus/` | the documents (fictional "Nimbus" cloud storage company docs) |

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # put your Google API key in LLM_API_KEY
uvicorn backend.main:app --reload
# open http://localhost:8000
```

With Docker:

```bash
docker build -t rag-v1 . && docker run -p 8000:8000 --env-file .env rag-v1
```

The first start downloads the embedding model (about 80 MB) and indexes `corpus/`. Later starts reuse `chroma_db/`.

## Evaluate retrieval

```bash
python -m eval.run_eval
```

Prints a hit or miss per question and saves the run with its settings to `eval/results/`.

## API

| Method | Path | |
|---|---|---|
| GET/POST | `/api/documents` | list / upload a .md or .txt file |
| DELETE | `/api/documents/{name}` | delete a document and its chunks |
| GET/PUT | `/api/settings` | chunk_size, overlap_percent, top_k |
| POST | `/api/ask` | `{question, documents[]}` returns `{status, answer, references, retrieved}` |
| GET | `/api/chunks/{id}` | full text of one chunk |
