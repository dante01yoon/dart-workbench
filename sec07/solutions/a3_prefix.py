"""과제 3 풀이: 임베딩할 때 청크 앞에 "회사 연도 사업보고서 · 섹션 경로"를 붙이면? (9편 Contextual Retrieval의 맛보기)
사용: uv run python sec07/solutions/a3_prefix.py"""

import _lab  # noqa: F401
import rag

chunks, emb = rag.load_store()
qs = rag.eval_questions()
qv = rag.unit(rag.embed([q["q"] for q in qs])[0])
vecs, tokens, cost = rag.embed(
    [f"{c['corp']} {c['year']} 사업보고서 · {c['section']}\n{c['text']}" for c in chunks]
)
emb2 = rag.unit(vecs)
for label, e in (("본문만", emb), ("앞에 회사·섹션", emb2)):
    for f in (False, True):
        rec, mrr, _ = rag.scorecard(chunks, e, qs, qv, f)
        print(f"{label:9s} {'필터' if f else '필터 없음':5s}  recall@5 {rec / len(qs):.3f}  MRR@10 {mrr:.3f}")
print(f"다시 임베딩 ${cost:.4f}")
