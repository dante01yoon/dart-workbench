"""29편 LLM 판사 v2 — 27편 루브릭(채점 기준표) 기준 하나에 판사 호출 하나.

판사 지시문에 넣는 것: 기준 문장 · 통과 예 · 실패 예 · 판단 재료(R2는 정답 정보, R6은 근거) · 이유를 먼저 쓰고 판정.
통과 · 실패 예는 채점할 26편 문항과 겹치지 않게 새로 썼다(시험 문항을 예시로 주면 시험지가 새는 것과 같다).
모델은 에이전트와 같은 deepseek-v4-flash(OpenRouter). 키는 .env에서 읽고 출력하지 않는다.
"""

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for d in ("sec09", "sec23", "sec27", "sec28"):
    sys.path.insert(0, str(ROOT / d))
from context import chat  # 9편 모델 호출(OpenRouter)
from grader import grade  # noqa: F401  28편 코드 채점기 v3(02_pairwise가 씀)

RB = importlib.import_module("01_rubric")  # 27편 루브릭 v1
RUBRIC = {r[0]: r for r in RB.RUBRIC}
TRACES = {x["id"]: x for x in map(json.loads, (ROOT / "data" / "traces26.jsonl").open())}
EXAMPLES = {
    "R2": (
        "질문: A사 2025년 매출액과 영업이익은? 정답 항목: 매출액 / 영업이익 → 답에 둘 다 있음 → 통과",
        "질문: B사 사외이사 명단은? 정답 항목: 이름 5개 → 답에 3명만 있음 → 실패",
    ),
    "R6": (
        "근거: 직원 수 1,000명. 답: 직원 수는 1,000명이다. → 답의 모든 내용이 근거에 있음 → 통과",
        "근거: 직원 수 1,000명. 답: 직원 수는 1,000명이고 평균 연봉은 1억 원이다. → 평균 연봉은 근거에 없음 → 실패",
    ),
}
V1 = (
    '[질문]이 묻는 항목을 [답]이 모두 답했나? 예/아니오 하나만 JSON으로: {"pass": true}'  # 27편 지시문 그대로
)


def answer(report):
    return "\n".join(
        f"{i}. {s['sentence']} (인용: {', '.join(s['cites']) or '없음'})" for i, s in enumerate(report, 1)
    )


def evidence(x):
    return "\n".join(f"{e['id']} [{e['source']}] {e['claim']}" for e in x["evidence"])


def gold(x):
    return " / ".join(g[0] for g in x["keys"])


def prompt_v1(x, report):
    return f"{V1}\n\n[질문] {x['q']}\n[답] {' '.join(s['sentence'] for s in report)}"


def prompt_v2(rid, x, report):
    _, name, question, *_ = RUBRIC[rid]
    good, bad = EXAMPLES[rid]
    info = f"[정답 정보] 공시에서 확인된 항목: {gold(x)}" if rid == "R2" else f"[근거]\n{evidence(x)}"
    return f"""너는 공시 리서치 답을 채점하는 판사다. 기준 하나만 본다.
[기준 {rid} {name}] {question}
[통과 예] {good}
[실패 예] {bad}
[질문] {x["q"]}
{info}
[답]
{answer(report)}
먼저 판단 이유를 한두 문장으로 쓰고, 그다음 판정하라. JSON 하나로: {{"reason": "...", "pass": true}}"""


def prompt_all(x, report):
    rules = "\n".join(f"{rid} {r[1]}: {r[2]}" for rid, r in RUBRIC.items())
    return f"""너는 공시 리서치 답을 채점하는 판사다. 아래 기준 6개를 한 번에 모두 판정하라.
{rules}
[질문] {x["q"]}
[정답 정보] 공시에서 확인된 항목: {gold(x) if x["keys"] != "refuse" else "없음(거절해야 하는 문항)"}
[근거]
{evidence(x)}
[답]
{answer(report)}
먼저 이유를 짧게 쓰고, 기준마다 예/아니오. JSON 하나로: {{"reason": "...", "R1": true, "R2": true, "R3": true, "R4": true, "R5": true, "R6": true}}"""


def ask(prompt):
    """판사 한 번 부르기 → (JSON 판정, 비용). 생각에 한도를 다 써서 빈 답이면 한도를 늘려 한 번 더."""
    cost = 0.0
    for limit in (6000, 12000):
        raw, u = chat(prompt, max_tokens=limit)
        cost += float(u.get("cost") or 0)
        try:
            return json.loads(raw[raw.index("{") : raw.rindex("}") + 1]), cost
        except ValueError:
            continue
    return {}, cost
