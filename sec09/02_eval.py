"""9편 ② 맥락 문장을 붙이면 검색이 얼마나 좋아질까? 키워드 · 벡터 · 하이브리드를 맥락 없이 / 맥락 붙여서 잰다.
회사 필터, 2025년 문항 38개 × 원래 질문 · 말 바꾼 질문. 맥락 붙인 벡터는 처음 한 번 다시 임베딩한다(약 $0.07).
사용: uv run python sec09/02_eval.py"""

import numpy as np
from context import DIR, load_context
from search import BM25, doc_text, embed, eval_questions, first_hit, keyword, load_store, rrf, unit, vector

chunks, emb = load_store()
ctx = load_context()
print(f"맥락 문장 {len(ctx):,} / {len(chunks):,}개")
path = DIR / "emb_ctx.npy"
if not path.exists():
    vecs, tokens, cost = embed([f"{ctx.get(c['id'], '')}\n{c['text']}" for c in chunks])
    np.save(path, np.array(vecs, dtype=np.float32))
    print(f"맥락 + 조각 다시 임베딩: {tokens:,}토큰 · ${cost:.4f}")
emb_ctx = unit(np.load(path))
bm = BM25([doc_text(c) for c in chunks])
bm_ctx = BM25([ctx.get(c["id"], "") + " " + doc_text(c) for c in chunks])
qs = eval_questions()
for label, field in (("원래 질문", "q"), ("말 바꾼 질문", "q_para")):
    qv = unit(embed([q[field] for q in qs])[0])
    print(f"■ {label}")
    for name, b, e in (("맥락 없음", bm, emb), ("맥락 붙임", bm_ctx, emb_ctx)):
        res = {"keyword": [], "vector": [], "hybrid": []}
        for q, v in zip(qs, qv):
            kw = keyword(b, chunks, q[field], 50, q["corp"])
            ve = vector(e, chunks, v, 50, q["corp"])
            for m, r in (("keyword", kw), ("vector", ve), ("hybrid", rrf(kw, ve, k=10))):
                res[m].append(first_hit(chunks, r[:10], q))
        line = "  ".join(
            f"{m} {sum(h is not None and h < 5 for h in hs) / len(qs):.3f}" for m, hs in res.items()
        )
        print(f"  {name}  recall@5  {line}")
