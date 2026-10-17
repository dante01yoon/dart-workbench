"""검색 성적표: recall@5, MRR@10을 LLM 없이 계산한다.

평가 세트(eval/questions.jsonl) 한 줄:
  {"id", "type", "q", "corp", "year", "gold": {"section": "부분 문자열", "contains": ["정답 문자열", ...]}}
정답 청크 = 섹션 경로에 gold.section이 들어 있고, 본문에 gold.contains 중 하나가 들어 있는 청크.
답이 없는 문항(type=none, refuse)은 검색 성적에서 뺀다.

사용: python -m dart_rag.evaluate [keyword|vector|hybrid ...] [--filter] [--para] [--ctx]  (--para = 말 바꾼 질문, --ctx = Contextual Retrieval)
"""

import json
import sys
import time
from collections import defaultdict

from . import dart
from .search import Searcher, build_vectors, load_chunks, load_context

QFILE = dart.ROOT / "eval" / "questions.jsonl"


def is_gold(c, g, q):
    if q.get("corp") and c["corp"] != q["corp"]:
        return False
    if q.get("year") and c["year"] != q["year"]:
        return False
    if g.get("section") and g["section"] not in c["section"]:
        return False
    return any(s in c["text"] for s in g["contains"])


def run(methods, use_filter=False, para=False, use_ctx=False):
    chunks = load_chunks()
    qs = [json.loads(l) for l in QFILE.open(encoding="utf-8") if l.strip()]
    qs = [q for q in qs if q.get("gold")]
    ctx = load_context() if use_ctx else None
    vec = build_vectors(chunks, ctx) if any(m != "keyword" for m in methods) else None
    s = Searcher(chunks, vec, ctx)
    report = {}
    for m in methods:
        rec, mrr, by_type, t0 = 0, 0.0, defaultdict(lambda: [0, 0]), time.time()
        misses = []
        for q in qs:
            f = {"corp": q.get("corp"), "year": q.get("year")} if use_filter else {}
            ranked = getattr(s, m)(q["q_para"] if para else q["q"], k=10, **f)
            hit = next((r for r, i in enumerate(ranked) if is_gold(chunks[i], q["gold"], q)), None)
            ok = hit is not None and hit < 5
            rec += ok
            mrr += 1 / (hit + 1) if hit is not None else 0
            by_type[q["type"]][0] += ok
            by_type[q["type"]][1] += 1
            if not ok:
                misses.append((q["id"], q["q"], chunks[ranked[0]]["section"] if ranked else "-"))
        n = len(qs)
        report[m] = {"recall@5": round(rec / n, 3), "mrr@10": round(mrr / n, 3), "n": n,
                     "sec_per_q": round((time.time() - t0) / n, 3),
                     "by_type": {k: f"{a}/{b}" for k, (a, b) in sorted(by_type.items())}, "misses": misses}
    return report


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")] or ["keyword", "vector", "hybrid"]
    r = run(args, "--filter" in sys.argv, "--para" in sys.argv, "--ctx" in sys.argv)
    for m, v in r.items():
        print(f"{m:8s} recall@5 {v['recall@5']:.3f}  MRR@10 {v['mrr@10']:.3f}  ({v['n']}문항, {v['sec_per_q']}s/문항)  {v['by_type']}")
    name = "scorecard" + ("-filter" if "--filter" in sys.argv else "") + ("-para" if "--para" in sys.argv else "") + ("-ctx" if "--ctx" in sys.argv else "")
    out = dart.ROOT / "eval" / f"{name}.json"
    old = json.loads(out.read_text()) if out.exists() else {}
    out.write_text(json.dumps({**old, **r}, ensure_ascii=False, indent=1))
