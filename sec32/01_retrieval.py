"""32편 ① 검색 평가 — Recall@k · MRR, 그리고 "검색 문제냐 생성 문제냐" 나누기.

- 26편 실행 기록에서 에이전트가 실제로 낸 공시 검색어(계획의 filings 작업)를 그대로 다시 검색한다(같은 검색기, k=10).
  모델 호출 없음. 검색어 임베딩만 부른다(검색어 하나에 1원도 안 된다).
- 정답 섹션: 첫 정답 키(사실 · 숫자)가 들어 있는 그 회사 보고서 섹션(agent_eval.gold_sections). 섹션이 5곳보다 많으면 뺀다.
- Recall@k는 "정답 섹션이 상위 k 안에 하나라도 있나"로 센다(정답 섹션 하나면 답할 수 있다 · hit rate라고도 부른다).
  정답 섹션 중 몇 곳을 찾았나로 세는 원래 정의는 과제 1.
- 그날 에이전트가 본 것은 상위 6개다 → Recall@6이 "에이전트가 정답 문단을 받았나"다.
- 틀린 문항은 세 칸으로 나눈다: 검색(상위 6 안에 정답 섹션) → 근거(뽑은 근거에 정답 키) → 답(보고서에 정답 키).
  답에 정답 키(28편 v3 키)가 있는데 틀림이면 채점 문제다(그날 채점기는 22편 v2).
사용: uv run python sec32/01_retrieval.py → data/eval32_retrieval.json
"""

import sys

from agent_eval import (
    MAX_GOLD,
    ROOT,
    chunks,
    first_hit,
    gold_sections,
    has_key,
    keys_of,
    mrr,
    plan,
    recall_at,
    report_text,
    save,
    traces,
)

sys.path.insert(0, str(ROOT / "sec10"))
from cite import Store  # 10편 검색기 = 워크벤치 search_filings가 쓰는 것과 같다

store, chs = Store(), chunks()
rows = []
for x in traces():
    gold = gold_sections(x, chs)
    tasks = [t for t in plan(x) or [] if t["worker"] == "filings"]
    if not gold or len(gold) > MAX_GOLD or not tasks:
        continue
    ranked = [[chs[i]["section"] for i in store.search(t["query"], t.get("corp"), k=10)] for t in tasks]
    ranks = [first_hit(r, set(gold)) for r in ranked]
    rank = min((r for r in ranks if r), default=None)  # 검색 작업이 둘이면 더 잘 찾은 쪽
    seen = {e["source"].split(" · ", 1)[1] for e in x["evidence"] if "사업보고서" in e["source"]}
    ev = " ".join(e["claim"] + " " + e["quote"] for e in x["evidence"])
    rows.append(
        {
            "id": x["id"],
            "q": x["q"],
            "correct": x["correct"],
            "queries": [t["query"] for t in tasks],
            "gold": gold,
            "rank": rank,
            "same_as_run": seen
            <= {s for r in ranked for s in r[:6]},  # 그날 뽑은 근거 섹션이 다시 뽑은 상위 6 안에 있나
            "in_evidence": has_key(keys_of(x), ev),
            "in_report": has_key(keys_of(x), report_text(x)),
        }
    )

ranks = [r["rank"] for r in rows]
print(f"검색 채점 {len(rows)}문항 (정답 섹션 1~{MAX_GOLD}곳 + 공시 검색을 한 문항, 개발 48 + 24편 실패 5 중)")
print(
    f"다시 검색한 순위가 그날과 같은가: 그날 근거 섹션이 다시 뽑은 상위 6 안 {sum(r['same_as_run'] for r in rows)}/{len(rows)}"
)
for k in (1, 3, 6, 10):
    print(
        f"  Recall@{k:<2} {recall_at(ranks, k) * 100:5.1f}%" + ("   ← 에이전트가 본 상위 6" if k == 6 else "")
    )
print(f"  MRR      {mrr(ranks):.3f}  (1이면 늘 1위, 0.5면 대개 2위 · 못 찾으면 0으로 셈)")

print(
    "\n틀린 문항 — 어디서 끊겼나 (검색 = 상위 6에 정답 섹션 · 근거 = 뽑은 근거에 정답 키 · 답 = 보고서에 정답 키)"
)
for r in rows:
    if r["correct"]:
        continue
    found = r["rank"] is not None and r["rank"] <= 6
    stage = (
        "채점" if r["in_report"] else "검색" if not found else "근거 뽑기" if not r["in_evidence"] else "작성"
    )
    mark = lambda b: "O" if b else "X"
    print(
        f"  {r['id']:4s} 검색 {mark(found)}({r['rank'] or '-'}위) → 근거 {mark(r['in_evidence'])} → 답 {mark(r['in_report'])}"
        f"  ⇒ {stage} 문제  {r['q'][:24]}"
    )
miss = [r for r in rows if r["correct"] and not (r["rank"] and r["rank"] <= 6)]
print(
    f"\n맞혔는데 검색은 놓친 문항 {len(miss)}개: {' '.join(r['id'] for r in miss)} — 재무 API · 뉴스로 답했다"
)
save("eval32_retrieval.json", rows)
print("기록 → data/eval32_retrieval.json")
