"""Retrieval baseline: how often is the right passage in the top-k?

A question is a hit when one of the top-k chunks comes from the expected file
AND contains the evidence sentence. Using an evidence string instead of a chunk id
keeps the number comparable when chunk size changes (V1 vs V2).

Usage: python -m eval.run_eval            (uses the current settings)
"""
import json
import time
from pathlib import Path

from backend import rag

HERE = Path(__file__).parent


def norm(s: str) -> str:
    return " ".join(s.split()).lower()


def main():
    settings = rag.load_settings()
    questions = json.loads((HERE / "questions.json").read_text())
    docs = rag.list_documents()
    rows, hits, ranks, answerable = [], 0, [], 0
    for q in questions:
        chunks = rag.retrieve(q["question"], docs, settings["top_k"])
        rank = None
        if q["evidence"]:
            answerable += 1
            for i, c in enumerate(chunks, 1):
                if c["source"] == q["source"] and norm(q["evidence"]) in norm(c["text"]):
                    rank = i
                    break
            hits += rank is not None
            ranks.append(1 / rank if rank else 0)
        rows.append({"question": q["question"], "type": q["type"], "rank": rank,
                     "top_score": chunks[0]["score"] if chunks else None,
                     "top_source": chunks[0]["source"] if chunks else None})
        mark = "-" if not q["evidence"] else ("HIT @%d" % rank if rank else "MISS")
        print(f"{mark:8} {chunks[0]['score'] if chunks else '':>6}  [{q['type']}] {q['question']}")

    summary = {"settings": settings, "answerable_questions": answerable,
               f"hit_rate@{settings['top_k']}": round(hits / answerable, 3),
               "mrr": round(sum(ranks) / answerable, 3)}
    print(json.dumps(summary, indent=2))
    out = HERE / "results" / f"{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
