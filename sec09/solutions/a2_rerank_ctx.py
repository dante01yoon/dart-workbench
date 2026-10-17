"""과제 2 풀이: 맥락 붙인 하이브리드 상위 20개에 8편 재정렬을 걸면? (Flash 재정렬 38번 × 2, 약 $0.14)
사용: uv run python sec09/solutions/a2_rerank_ctx.py"""

from concurrent.futures import ThreadPoolExecutor

import _lab  # noqa: F401
import numpy as np
from context import DIR, load_context
from search import (
    BM25,
    doc_text,
    embed,
    eval_questions,
    first_hit,
    keyword,
    load_store,
    rerank,
    rrf,
    unit,
    vector,
)

chunks, _ = load_store()
ctx = load_context()
emb_ctx = unit(np.load(DIR / "emb_ctx.npy"))
bm = BM25([ctx.get(c["id"], "") + " " + doc_text(c) for c in chunks])
qs = eval_questions()
for field in ("q", "q_para"):
    qv = unit(embed([q[field] for q in qs])[0])
    cands = [
        rrf(keyword(bm, chunks, q[field], 50, q["corp"]), vector(emb_ctx, chunks, v, 50, q["corp"]), k=20)
        for q, v in zip(qs, qv)
    ]
    with ThreadPoolExecutor(4) as ex:
        rr = list(ex.map(lambda a: rerank(chunks, a[0], a[1]), zip([q[field] for q in qs], cands)))
    hy = sum((h := first_hit(chunks, c[:10], q)) is not None and h < 5 for c, q in zip(cands, qs)) / len(qs)
    re_ = sum((h := first_hit(chunks, r, q)) is not None and h < 5 for (r, _), q in zip(rr, qs)) / len(qs)
    print(
        f"{'원래 질문' if field == 'q' else '말 바꾼 질문':7s} 맥락 하이브리드 {hy:.3f} → 재정렬 {re_:.3f}  비용 ${sum(c for _, c in rr):.4f}"
    )
