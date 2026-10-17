"""과제 2 풀이: RRF의 상수 c(60 · 10)와 가중치(키워드 2배)를 바꾸면 하이브리드가 BM25를 넘을까? (질문 임베딩만, 약 $0.001)
사용: uv run python sec08/solutions/a2_rrf.py"""

from collections import Counter

import _lab  # noqa: F401
from search import BM25, doc_text, embed, eval_questions, first_hit, keyword, load_store, unit, vector


def rrf_w(kw, ve, k=10, c=60, wk=1.0, wv=1.0):
    s = Counter()
    for w, lst in ((wk, kw), (wv, ve)):
        for r, i in enumerate(lst):
            s[i] += w / (c + r + 1)
    return [i for i, _ in s.most_common(k)]


chunks, emb = load_store()
bm = BM25([doc_text(c) for c in chunks])
qs = eval_questions()
for field in ("q", "q_para"):
    qv = unit(embed([q[field] for q in qs])[0])
    pairs = [
        (keyword(bm, chunks, q[field], 50, q["corp"]), vector(emb, chunks, v, 50, q["corp"]))
        for q, v in zip(qs, qv)
    ]
    print(f"■ {'원래 질문' if field == 'q' else '말 바꾼 질문'}")
    for label, kw_args in (
        ("c=60 (본편)", {}),
        ("c=10", {"c": 10}),
        ("c=60 · 키워드 2배", {"wk": 2.0}),
        ("c=60 · 키워드 3배", {"wk": 3.0}),
    ):
        hits = [first_hit(chunks, rrf_w(kw, ve, **kw_args), q) for (kw, ve), q in zip(pairs, qs)]
        print(f"  {label:16s} recall@5 {sum(h is not None and h < 5 for h in hits) / len(qs):.3f}")
