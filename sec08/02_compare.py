"""8편 ② 검색 4종 성적표: 키워드(BM25) · 벡터 · 하이브리드(RRF) · 재정렬. 회사 필터를 건 상태에서,
원래 질문(보고서 단어를 그대로 씀)과 말 바꾼 질문(q_para) 두 벌로 잰다. 2025년 문항 38개.
재정렬은 하이브리드 상위 20개를 Flash가 다시 줄 세운다(질문당 호출 1번).
사용: uv run python sec08/02_compare.py → data/rag/compare.json"""

import json
from concurrent.futures import ThreadPoolExecutor

from search import (
    BM25,
    DIR,
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

chunks, emb = load_store()
bm = BM25([doc_text(c) for c in chunks])
qs = eval_questions()
out = {}
for label, field in (("원래 질문", "q"), ("말 바꾼 질문", "q_para")):
    texts = [q[field] for q in qs]
    qv = unit(embed(texts)[0])
    runs = {"keyword": [], "vector": [], "hybrid": []}
    for q, t, v in zip(qs, texts, qv):
        kw = keyword(bm, chunks, t, k=50, corp=q["corp"])
        ve = vector(emb, chunks, v, k=50, corp=q["corp"])
        runs["keyword"].append(kw[:10])
        runs["vector"].append(ve[:10])
        runs["hybrid"].append(rrf(kw, ve, k=20))
    with ThreadPoolExecutor(4) as ex:
        rr = list(ex.map(lambda a: rerank(chunks, a[0], a[1]), zip(texts, runs["hybrid"])))
    runs["rerank"] = [r for r, _ in rr]
    cost = sum(c for _, c in rr)
    print(f"■ {label} ({len(qs)}문항, 회사 필터)")
    out[label] = {}
    for m, ranked in runs.items():
        hits = [first_hit(chunks, r[:10], q) for r, q in zip(ranked, qs)]
        rec = sum(h is not None and h < 5 for h in hits) / len(qs)
        mrr = sum(1 / (h + 1) for h in hits if h is not None) / len(qs)
        out[label][m] = {"recall@5": round(rec, 3), "mrr@10": round(mrr, 3), "ranked": ranked}
        extra = f"  (재정렬 비용 ${cost:.4f})" if m == "rerank" else ""
        print(f"  {m:8s} recall@5 {rec:.3f}  MRR@10 {mrr:.3f}{extra}")
(DIR / "compare.json").write_text(json.dumps(out, ensure_ascii=False))
print("저장 → data/rag/compare.json   순위 화면: uv run python sec08/03_rank_web.py")
