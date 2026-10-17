"""과제 1 풀이: 모델이 쓴 맥락 문장 대신 "회사 연도 사업보고서 · 섹션 경로" 머리말만 붙이면? (7편 과제 3 방식, 다시 임베딩 약 $0.06)
사용: uv run python sec09/solutions/a1_header.py"""

import _lab  # noqa: F401
import numpy as np
from context import DIR, load_context
from search import embed, eval_questions, first_hit, load_store, unit, vector

chunks, emb = load_store()
ctx = load_context()
emb_ctx = unit(np.load(DIR / "emb_ctx.npy"))
vecs, _, cost = embed([f"{c['corp']} {c['year']} 사업보고서 · {c['section']}\n{c['text']}" for c in chunks])
emb_head = unit(vecs)
qs = eval_questions()
for field in ("q", "q_para"):
    qv = unit(embed([q[field] for q in qs])[0])
    line = f"{'원래 질문' if field == 'q' else '말 바꾼 질문':7s}"
    for name, e in (("본문만", emb), ("머리말", emb_head), ("모델 맥락", emb_ctx)):
        hits = [first_hit(chunks, vector(e, chunks, v, 10, q["corp"]), q) for q, v in zip(qs, qv)]
        line += f"  {name} {sum(h is not None and h < 5 for h in hits) / len(qs):.3f}"
    print(line + "  (벡터 recall@5)")
print(f"머리말 임베딩 ${cost:.4f}")
