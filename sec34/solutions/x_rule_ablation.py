"""34편 덧붙임 풀이 — 지시문 v2에 넣은 규칙 세 줄 중 무엇이 어느 문항을 고쳤나(하나씩 빼 보기). 계획 담당만 부른다.

계획이 맞았는지는 계획 모양으로 본다(에이전트 전체는 돌리지 않는다):
  n14 · q38 → filings 작업이 있나 / q32 → 검색어에 2025가 있고 2023이 없나 / q51 · q52 · q54 → 거절했나
같은 지시문도 부를 때마다 계획이 달라질 수 있어 조건마다 4번씩 부른다.
사용: uv run python sec34/solutions/x_rule_ablation.py
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from planner_v2 import ADDED, PLAN_FAILS, PLANNER_V2
from team import PLANNER, chat, parse

QS = {
    "n14": "현대자동차 2025 재고자산 금액",
    "q38": "SK하이닉스와 삼성전자의 2025년 주당 배당금 비교",
    "q32": "삼성전자 연구개발비 비율은 전년보다 늘었나 줄었나?",
    "q51": "삼성전자의 2027년 매출 전망치는?",
    "q52": "카카오의 2026년 3분기 영업이익은?",
    "q54": "현대자동차 다음 신차 출시일은?",
}
RULES = ADDED.splitlines()[1:]  # 첫 줄은 머리말, 나머지 세 줄이 규칙
NAMES = ["재무 도구 범위", "연도 기본값", "미공시는 거절"]


def ok(i, plan):
    qs = " ".join(t.get("query", "") for t in plan.get("tasks", []))
    if i in ("n14", "q38"):
        return any(t.get("worker") == "filings" for t in plan.get("tasks", []))
    if i == "q32":
        return "2025" in qs and "2023" not in qs
    return bool(plan.get("refuse"))


def without(k):
    return PLANNER_V2.replace(RULES[k] + "\n", "")


PROMPTS = {"v1(원래)": PLANNER, "v2(세 줄 모두)": PLANNER_V2} | {
    f"v2 − {NAMES[k]}": without(k) for k in range(3)
}
jobs = [(name, i, r) for name in PROMPTS for i in PLAN_FAILS for r in range(4)]


def call(job):
    name, i, _ = job
    raw, u = chat(f"{PROMPTS[name]}\n\n질문: {QS[i]}", max_tokens=6000)
    return ok(i, parse(raw)), float(u.get("cost") or 0)


with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(call, jobs))
print("지시문            " + "  ".join(f"{i:>4s}" for i in PLAN_FAILS) + "   맞은 계획")
for name in PROMPTS:
    cells = [sum(r[0] for j, r in zip(jobs, res) if j[0] == name and j[1] == i) for i in PLAN_FAILS]
    print(f"{name:16s}  " + "  ".join(f" {c}/4" for c in cells) + f"   {sum(cells)}/24")
print(f"\n계획 담당 {len(jobs)}번 · ${sum(r[1] for r in res):.4f}")
