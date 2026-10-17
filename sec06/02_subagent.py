"""6편 ② 서브에이전트로 컨텍스트 나누기.

과제: 4개사 2025년 배당을 dividend-check 스킬대로 점검하고 마지막에 비교표를 만든다.
혼자      메인 에이전트가 공시 도구를 직접 불러 네 회사를 다 점검한다. 도구 결과가 메인 대화에 쌓인다.
서브      메인은 delegate(회사)만 부른다. 서브에이전트가 새 대화에서 점검하고 짧은 보고만 돌려준다.
지표: 비교표에 맞는 주당배당금이 몇 개 들어갔나(4개), 메인 호출별 입력 토큰, 서브 호출 토큰, 합계, 비용
사용: uv run python sec06/02_subagent.py → data/subagent_runs.json   막대: uv run python sec06/03_bars.py
"""

import json
import re
import time

from skills import ROOT, SKILLS, TOOLS, loop, run_tool

CORPS = ["삼성전자", "SK하이닉스", "현대자동차", "카카오"]
YEAR = 2025
SKILL = SKILLS["dividend-check"]["body"]
WORK = [t for t in TOOLS if t["function"]["name"] in ("dividends", "key_accounts")]
DELEGATE = {
    "type": "function",
    "function": {
        "name": "delegate",
        "description": "회사 하나의 배당 점검을 서브에이전트에게 맡긴다. 서브에이전트가 공시를 조회해 짧은 보고를 돌려준다.",
        "parameters": {
            "type": "object",
            "properties": {"corp": {"type": "string", "enum": CORPS}},
            "required": ["corp"],
        },
    },
}
TASK = "삼성전자, SK하이닉스, 현대자동차, 카카오의 2025년 배당을 회사마다 점검하고, 마지막에 네 회사의 주당배당금·배당성향 비교표를 만들어라."


def gold():
    """정답: 2025년 보통주 주당 현금배당금을 우리 코드가 직접 조회한다."""
    out = {}
    for c in CORPS:
        rows = run_tool("dividends", {"corp": c, "year": YEAR})["rows"]
        out[c] = next(
            x["thstrm"] for x in rows if x["se"].startswith("주당 현금배당금") and x["stock_knd"] == "보통주"
        )
    return out


def score(final, g):
    """비교표에 나온 숫자들 중 정답 주당배당금이 몇 개 있나(쉼표는 무시, 숫자 단위로 비교)."""
    nums = {n.replace(",", "") for n in re.findall(r"\d[\d,]*", final)}
    return sum(v.replace(",", "") in nums for v in g.values())


def solo(g):
    t0 = time.time()
    system = "너는 공시 분석가다. 아래 스킬의 절차를 따르라.\n\n" + SKILL
    final, calls, _ = loop(system, TASK, WORK, max_turns=20)
    return {
        "mode": "solo",
        "main": [c["in"] for c in calls],
        "subs": [],
        "cost": sum(c["cost"] for c in calls),
        "ok": score(final, g),
        "seconds": round(time.time() - t0),
        "final": final[:2000],
    }


REPORT = "결과만 짧게 보고하라."  # 서브에이전트에게 주는 보고 지시(과제 2에서 바꾼다)
CHECK = True  # 메인이 일을 덜 끝내고 멈추면 하네스가 다시 시킨다(녹화 첫 실행은 이것 없이 0/4)


def team(g):
    t0 = time.time()
    subs, cost = [], 0.0

    def delegate(args):
        nonlocal cost
        corp = args.get("corp")
        system = f"너는 공시 분석가다. 아래 스킬의 절차를 따르고, {REPORT}\n\n" + SKILL
        final, calls, _ = loop(system, f"{corp} {YEAR}년 배당 점검", WORK)
        subs.append({"corp": corp, "calls": [c["in"] for c in calls]})
        cost += sum(c["cost"] for c in calls)
        return final

    system = "너는 팀장이다. 회사마다 delegate로 서브에이전트에게 점검을 맡기고, 돌아온 보고만 모아 비교표를 만들어라."

    def check(final):  # 완료 확인: 안 맡긴 회사가 있거나 답이 비었으면 다시 시킨다
        left = [c for c in CORPS if c not in {s["corp"] for s in subs}]
        if left:
            return f"아직 맡기지 않은 회사: {', '.join(left)}. 마저 맡긴 뒤 비교표를 써라."
        if not final:
            return "네 회사 보고가 모두 왔다. 이제 비교표를 써라."
        return None

    final, calls, _ = loop(
        system, TASK, [DELEGATE], extra={"delegate": delegate}, max_turns=10, check=check if CHECK else None
    )
    cost += sum(c["cost"] for c in calls)
    return {
        "mode": "team",
        "main": [c["in"] for c in calls],
        "subs": subs,
        "cost": cost,
        "ok": score(final, g),
        "seconds": round(time.time() - t0),
        "final": final[:2000],
    }


def main():
    g = gold()
    out = []
    for f, label in ((solo, "혼자"), (team, "서브에이전트")):
        r = f(g)
        out.append(r)
        sub_total = sum(sum(s["calls"]) for s in r["subs"])
        print(
            f"{label:7s} 주당배당금 {r['ok']}/4  메인 호출 {len(r['main'])}번  메인 입력 {sum(r['main']):,}  최대 {max(r['main']):,}  "
            f"서브 입력 {sub_total:,}  합계 {sum(r['main']) + sub_total:,}  ${r['cost']:.4f}  {r['seconds']}초",
            flush=True,
        )
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "subagent_runs.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("저장 → data/subagent_runs.json   막대: uv run python sec06/03_bars.py")


if __name__ == "__main__":
    main()
