"""직접 구현 vs LangChain vs LlamaIndex — 같은 42문항, 같은 임베딩, 같은 필터 (강의 11편).
사용: .venv/bin/python frameworks/compare.py [--para] → data/frameworks.json
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dart_rag import dart  # noqa: E402
from dart_rag.evaluate import QFILE, is_gold  # noqa: E402
from dart_rag.search import Searcher, build_vectors, load_chunks  # noqa: E402

para = "--para" in sys.argv
chunks = load_chunks()
qs = [q for q in map(json.loads, QFILE.open(encoding="utf-8")) if q.get("gold")]


def score(fn):
    rec = mrr = 0
    t0 = time.time()
    for q in qs:
        ids = fn(q["q_para"] if para else q["q"], q["corp"], q["year"])
        hit = next((r for r, i in enumerate(ids) if is_gold(chunks[i], q["gold"], q)), None)
        rec += hit is not None and hit < 5
        mrr += 1 / (hit + 1) if hit is not None else 0
    return {"recall@5": round(rec / len(qs), 3), "mrr@10": round(mrr / len(qs), 3), "sec_per_q": round((time.time() - t0) / len(qs), 3)}


rows = []
own = Searcher(chunks, build_vectors(chunks))
for kind in ("keyword", "vector", "hybrid"):
    rows.append({"impl": "직접", "kind": kind, **score(lambda q, c, y: getattr(own, kind)(q, k=10, corp=c, year=y))})
    print(rows[-1], flush=True)

t0 = time.time()
from frameworks import lc_rag  # noqa: E402

lc_build = round(time.time() - t0, 1)
for kind, korean in (("keyword", False), ("keyword", True), ("vector", True), ("hybrid", True)):
    rows.append({"impl": "LangChain", "kind": kind + ("" if korean else " (기본 토크나이저)"), "build_s": lc_build,
                 **score(lambda q, c, y: lc_rag.search(q, kind, 10, c, y, korean))})
    print(rows[-1], flush=True)

t0 = time.time()
from frameworks import li_rag  # noqa: E402

li_build = round(time.time() - t0, 1)
for kind, korean in (("keyword", False), ("keyword", True), ("vector", True), ("hybrid", True)):
    rows.append({"impl": "LlamaIndex", "kind": kind + ("" if korean else " (기본 토크나이저)"), "build_s": li_build,
                 **score(lambda q, c, y: li_rag.search(q, kind, 10, c, y, korean))})
    print(rows[-1], flush=True)

(dart.ROOT / "data" / f"frameworks{'-para' if para else ''}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
