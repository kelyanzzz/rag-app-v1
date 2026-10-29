# REPORT - RAG app V1

## Team details

| Member | Worked on |
|---|---|
| TODO name | TODO |

## Decision log

> TODO: rewrite these entries in your own words before submitting.

**Corpus.** Options: a public domain novel, course material, a fictional company documentation set. Picked: fictional docs of a cloud storage company "Nimbus" (5 files, .md and .txt). Why: the LLM cannot know the answers from training, so a correct answer must come from retrieval; it contains error codes, policy vocabulary and numbers, which are realistic hard cases. Trade-off: it is small (about 9 KB), so retrieval is easier than on a large corpus.

**Stack.** FastAPI backend + one static HTML page served by FastAPI. Rejected: Next.js frontend, because two apps double the setup for a V1 whose point is the pipeline.

**Chunking.** Fixed 800-character windows with 10% overlap, after dropping paragraphs under 20 characters, as in `ask_rag_google.py`. Rejected for V1: splitting on headings or sentences. Kept naive so V2 has something to improve and measure.

**Embedding model.** all-MiniLM-L6-v2 (384 dimensions, 256 token input limit), run locally through Chroma's ONNX default. Free, private, no quota. Rejected: hosted embedding APIs (cost, data leaves the machine). Same model at index and query time because the collection carries the embedding function.

**Vector database.** ChromaDB persistent client, cosine distance. Each chunk stores `source` and `chunk_index` metadata so a question can be restricted to selected documents with a `where` filter, and a reference can be opened.

**LLM.** Gemini flash lite through the OpenAI SDK, configurable with `LLM_BASE_URL` / `LLM_MODEL` so any OpenAI-compatible provider works. Temperature 0 and JSON response mode.

**Response schema.** Pydantic model `{answerable: bool, answer: str, citations: [chunk ids]}`. Citations are checked against the chunks actually retrieved; invented ids are dropped and shown to the user.

**References.** A reference points to a chunk (file + chunk index), clickable to show its full text. Rejected for V1: line numbers, since character windows do not align with lines.

**Parameter changes.** Changing chunk size or overlap re-chunks and re-embeds every document. Changing top-k only changes the query, nothing is recomputed.

**Evaluation.** A hit means a top-k chunk comes from the expected file and contains an evidence sentence. Using an evidence string rather than a chunk id keeps the metric comparable when chunk size changes in V2. Metrics: hit rate@k and MRR.

## Controlled failures

| Situation | What the user sees (`status`) |
|---|---|
| No document selected | error message "Select at least one document" |
| Upload is not .md/.txt, not UTF-8, or empty | upload refused with the reason |
| No chunk above the similarity threshold (`MIN_SCORE`, 0.2) | `no_relevant_context`: "No passage looks related", no LLM call |
| Missing API key, network error, quota | `llm_error`, retrieved chunks still shown |
| LLM output is not valid JSON / does not match the schema | `invalid_llm_output`, no crash |
| LLM says the excerpts do not contain the answer | `not_in_documents` |
| LLM answers but cites no retrieved chunk | `unsupported_answer`, flagged in orange |
| LLM cites a chunk id that was not retrieved | citation dropped and listed |
| Reference opened after a re-index | 404 "Chunk not found" |

## Retrieval baseline

18 questions (15 answerable, 3 unanswerable) in `eval/questions.json`, including vocabulary mismatch, error codes, a needle, a calculation and a two-place question.

| Settings | hit rate@5 | MRR |
|---|---|---|
| chunk 800, overlap 10%, top-k 5 | 0.933 | 0.833 |

## Known failures

1. **Error codes.** "I got NMB-429, how long should I wait?" misses the right chunk. The embedding model does not match exact codes well, and the 800-char window splits the section. V2 idea: hybrid search with BM25.
2. **Unanswerable but similar questions pass the threshold.** "Does Nimbus have a region in Tokyo?" gets a top similarity of 0.49 (the regions chunk), so it goes to the LLM; only the prompt prevents a wrong answer. Similarity is an angle, not a confidence.
3. **Chunks cut mid-sentence and mix sections**, because windows ignore headings. Open a few chunks in the UI to see it.
4. **Two-place questions** ("Where was the company founded and where is it now?") depend on both facts landing in the top-k.
5. **Small corpus.** With about 15 chunks, top-5 returns a third of the corpus, which inflates the hit rate. To check on a larger corpus.
