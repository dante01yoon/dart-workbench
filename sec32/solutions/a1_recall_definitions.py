"""과제 1 — 정답의 단위와 Recall 정의를 바꾸면 숫자가 어떻게 바뀌나.

같은 19문항 · 같은 검색어(01_retrieval.py 기록)로:
- 본문: 섹션 단위 · "하나라도"(hit rate)
- (가) 섹션 단위 · 원래 정의: 정답 섹션 중 상위 k에 들어온 비율의 평균(Hamel FAQ의 Recall@k)
- (나) 청크(문단) 단위 · "하나라도": 정답 키가 들어 있는 바로 그 청크가 상위 k에 있나
모델 호출 없음(검색어 임베딩만). 사용: uv run python sec32/solutions/a1_recall_definitions.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent_eval import ROOT, chunks, corps_in, has_key, keys_of, load, mrr, recall_at, traces

sys.path.insert(0, str(ROOT / "sec10"))
from cite import Store

store, chs, rows = Store(), chunks(), load("eval32_retrieval.json")
tr = {x["id"]: x for x in traces()}
sec_hit, sec_frac, chunk_rank = {k: [] for k in (1, 3, 6, 10)}, {k: [] for k in (1, 3, 6, 10)}, []
for r in rows:
    x, corp = tr[r["id"]], corps_in(tr[r["id"]]["q"])[0]
    gold_chunks = {c["id"] for c in chs if c["corp"] == corp and has_key(keys_of(x)[:1], c["text"])}
    ids = [store.search(q, corp, k=10) for q in r["queries"]]
    best = min((next((i for i, c in enumerate(lst, 1) if c in gold_chunks), 99) for lst in ids), default=99)
    chunk_rank.append(best if best < 99 else None)
    for k in (1, 3, 6, 10):
        found = {chs[c]["section"] for lst in ids for c in lst[:k]} & set(r["gold"])
        sec_frac[k].append(len(found) / len(r["gold"]))
print(f"{len(rows)}문항 · 정답 섹션 평균 {sum(len(r['gold']) for r in rows) / len(rows):.1f}곳")
print("k    섹션·하나라도(본문)  섹션·원래 정의(비율)  청크·하나라도")
ranks = [r["rank"] for r in rows]
for k in (1, 3, 6, 10):
    print(
        f"{k:<4} {recall_at(ranks, k) * 100:12.1f}%  {sum(sec_frac[k]) / len(rows) * 100:16.1f}%"
        f"  {recall_at(chunk_rank, k) * 100:12.1f}%"
    )
print(f"MRR  섹션 {mrr(ranks):.3f} · 청크 {mrr(chunk_rank):.3f}")
