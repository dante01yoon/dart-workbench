"""과제 3 풀이: 재정렬 후보를 하이브리드 대신 BM25 상위 20개에서 가져오면? (Flash 재정렬, 약 $0.15 · 15분 안팎)
사용: uv run python sec08/solutions/a3_rerank_kw.py"""

from concurrent.futures import ThreadPoolExecutor

import _lab  # noqa: F401
from search import BM25, doc_text, eval_questions, first_hit, keyword, load_store, rerank

chunks, _ = load_store()
bm = BM25([doc_text(c) for c in chunks])
qs = eval_questions()
for field in ("q", "q_para"):
    cands = [keyword(bm, chunks, q[field], 20, q["corp"]) for q in qs]
    with ThreadPoolExecutor(4) as ex:
        rr = list(ex.map(lambda a: rerank(chunks, a[0], a[1]), zip([q[field] for q in qs], cands)))
    hits = [first_hit(chunks, r, q) for (r, _), q in zip(rr, qs)]
    rec = sum(h is not None and h < 5 for h in hits) / len(qs)
    print(
        f"{'원래 질문' if field == 'q' else '말 바꾼 질문':7s} BM25 → 재정렬 recall@5 {rec:.3f}  비용 ${sum(c for _, c in rr):.4f}"
    )
