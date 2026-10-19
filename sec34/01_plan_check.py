"""34편 ① 고친 지시문을 계획 단계만 먼저 돌려 본다 — 에이전트 전체를 돌리기 전에 싸게 확인.

26편 계획 실패 6문항: 저장된 v1 계획(traces26.jsonl의 plan 이벤트) vs 지시문 v2로 계획 담당만 한 번씩 호출.
계획 담당 호출은 문항당 1센트의 몇십 분의 1이다. 에이전트 전체(검색 · 작성 · 심판)는 02_rerun.py에서.
사용: uv run python sec34/01_plan_check.py   → data/plan34.json
"""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from planner_v2 import PLAN_FAILS, PLANNER_V2
from team import chat, parse

DATA = Path(__file__).resolve().parent.parent / "data"
traces = {x["id"]: x for x in map(json.loads, (DATA / "traces26.jsonl").open())}


def show(plan):
    """계획 한 줄: 거절이면 '거절', 아니면 작업마다 워커(회사) 검색어"""
    if plan.get("refuse"):
        return "거절 — 공시에 없는 질문"
    return " · ".join(
        f"{t['worker']}({t.get('corp') or '-'}) {t.get('query', '')[:18]}" for t in plan.get("tasks", [])
    )


def plan_v2(i):
    raw, usage = chat(f"{PLANNER_V2}\n\n질문: {traces[i]['q']}", max_tokens=6000)
    return parse(raw), float(usage.get("cost") or 0)


v1 = {}
for i in PLAN_FAILS:
    ev = next((e for e in traces[i]["events"] if e["type"] in ("plan", "refused")), {})
    v1[i] = {"refuse": True} if ev.get("type") == "refused" else {"tasks": ev.get("tasks", [])}
with ThreadPoolExecutor(6) as ex:
    v2 = dict(zip(PLAN_FAILS, ex.map(plan_v2, PLAN_FAILS)))

for i in PLAN_FAILS:
    print(f"{i}  {traces[i]['q']}")
    print(f"   v1  {show(v1[i])}")
    print(f"   v2  {show(v2[i][0])}")
cost = sum(c for _, c in v2.values())
print(f"\n계획 담당만 {len(PLAN_FAILS)}번 호출 · ${cost:.4f}")
out = {i: {"q": traces[i]["q"], "v1": v1[i], "v2": v2[i][0]} for i in PLAN_FAILS}
(DATA / "plan34.json").write_text(
    json.dumps({"cost": round(cost, 5), "items": out}, ensure_ascii=False, indent=1)
)
print("기록 → data/plan34.json  · 다음: uv run python sec34/02_rerun.py")
