"""7편 ③ 검색 성적표: recall@5와 MRR@10. LLM 없이 문자열로 채점한다.

정답 청크 = 회사가 같고, 섹션 경로에 gold.section이 들어 있고, 본문에 gold.contains 중 하나가 있는 청크.
recall@5 = 정답 청크가 상위 5개 안에 든 문항 비율. MRR@10 = 1 / (처음 맞힌 순위)의 평균(10위 밖이면 0).
2025년 보고서만 넣었으므로 2025년 문항(38개)만 잰다.
사용: uv run python sec07/03_eval.py"""

from rag import embed, eval_questions, load_store, scorecard, unit

chunks, emb = load_store()
qs = eval_questions()
qv = unit(embed([q["q"] for q in qs])[0])
for label, use_filter in (("필터 없음", False), ("회사·연도 필터", True)):
    rec, mrr, misses = scorecard(chunks, emb, qs, qv, use_filter)
    print(f"{label:8s} recall@5 {rec / len(qs):.3f} ({rec}/{len(qs)})  MRR@10 {mrr:.3f}")
    for m in misses[:4]:
        print(f"    ✗ {m[0][:34]:34s} → 1위: {m[1]} · {m[2][:40]}")
