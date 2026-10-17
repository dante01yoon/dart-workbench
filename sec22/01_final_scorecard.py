"""22편 ① 최종 성적표 — 같은 20문항(13편 평가 세트)을 처음 만든 에이전트와 지금의 워크벤치로 돌려 한 줄씩 남긴다.

- 처음: 1편 루프 v0(while 문 + 재무 도구 하나). 본문 검색 · 인용 · 심판이 없다.
- 지금: 20편 워크벤치(리서치 팀 + 공시 MCP 서버 + 인용 심판 + 반성 1회 + 비용 상한).
- 모델은 둘 다 deepseek-v4-flash로 맞춘다(모델이 아니라 구조를 비교한다).
- 채점은 13편과 같다: 정답 키워드가 답 또는 근거에 모두 있으면 정답, 근거 없음 · 투자 권유는 거절이나 "확인되지 않음"이면 정답.
사용: uv run python sec22/01_final_scorecard.py → data/scorecard.jsonl에 두 줄 추가 · data/final_eval.json
"""

import importlib.util
import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["MODEL"] = "deepseek/deepseek-v4-flash"  # 1편 하네스가 읽는 모델 이름
for p in ("sec01", "sec20", "sec12", "sec10"):
    sys.path.insert(0, str(ROOT / p))
spec = importlib.util.spec_from_file_location("harness1", ROOT / "sec01" / "03_harness.py")
harness1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness1)  # 1편 run(question, trace) · Trace
from cite import keys, questions  # 10편 문항 · 정답 키
from mcp_tools import McpTools  # 20편
from workbench import BudgetExceeded, Workbench  # 20편

IDS = ["q01", "q03", "q06", "q09", "q28", "q30", "q31", "q36", "q37", "q40"]
IDS += ["q44", "q45", "q47", "q49", "q15", "q17", "q51", "q54", "q56", "q59"]  # 13편과 같은 20문항
qs, ks = questions(), keys()
REFUSAL = ("확인되지 않", "투자 권유", "답변드릴 수 없", "답할 수 없", "알 수 없", "제공하지 않")


def flat(s):
    return "".join(s.split())


def grade(qid, text, refused=False):
    if ks[qid] == "refuse":
        return refused or not text.strip() or any(w in text for w in REFUSAL)
    return all(any(flat(k) in flat(text) for k in g) for g in ks[qid])


def show(who, x):
    print(
        f"{who} {x['id']} {'✅' if x['correct'] else '❌'} {x['seconds']:5.1f}초  {qs[x['id']]['q'][:28]}",
        flush=True,
    )
    return x


def run_first(qid):
    tr, t0 = harness1.Trace(), time.time()
    answer = harness1.run(qs[qid]["q"], tr)
    return show(
        "처음",
        {
            "id": qid,
            "correct": grade(qid, answer),
            "sentences": max(1, answer.count("다.")),
            "cited": 0,  # 인용 개념이 없다
            "supported": 0,
            "cost": sum(c["cost"] for c in tr.calls),
            "seconds": time.time() - t0,
            "answer": answer,
        },
    )


mcp = McpTools()


def run_now(qid):
    wb, t0 = Workbench(mcp, emit=lambda e: None, cap=0.05), time.time()
    try:
        r = wb.research(qs[qid]["q"])
    except BudgetExceeded:
        r = {"refused": False, "report": [], "evidence": []}
    rep = r.get("report", [])
    text = " ".join(s["sentence"] for s in rep) + " " + " ".join(e["claim"] for e in r.get("evidence", []))
    return show(
        "지금",
        {
            "id": qid,
            "correct": grade(qid, text, r.get("refused", False)),
            "sentences": len(rep),
            "cited": sum(bool(s["cites"]) for s in rep),
            "supported": sum(s["badge"] == "지지" for s in rep),
            "cost": wb.spent,
            "seconds": time.time() - t0,
            "rounds": r.get("rounds", 0),
            "report": rep,
        },
    )


def row(name, res):
    secs = sorted(x["seconds"] for x in res)
    n, sents = len(res), sum(x["sentences"] for x in res)
    return {
        "name": name,
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "n": n,
        "pass_rate": round(sum(x["correct"] for x in res) / n, 3),
        "tokens": 0,
        "cost_usd": round(sum(x["cost"] for x in res), 4),
        "cost_per_q": round(sum(x["cost"] for x in res) / n, 5),
        "p50_s": round(statistics.median(secs), 1),
        "p95_s": round(secs[min(n - 1, int(n * 0.95))], 1),
        "cited": f"{sum(x['cited'] for x in res)}/{sents}",
        "supported": f"{sum(x['supported'] for x in res)}/{sents}",
    }


def main(ids, label="20문항"):
    with ThreadPoolExecutor(4) as ex:
        first = list(ex.map(run_first, ids))
    print("처음 끝", sum(x["correct"] for x in first), "/", len(first))
    with ThreadPoolExecutor(4) as ex:
        now = list(ex.map(run_now, ids))
    mcp.close()

    rows = [row(f"22편 · 처음: 1편 루프 v0 · {label}", first), row(f"22편 · 지금: 워크벤치 · {label}", now)]
    with (ROOT / "data" / "scorecard.jsonl").open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (ROOT / "data" / ("final_eval.json" if label == "20문항" else "final_eval_mine.json")).write_text(
        json.dumps({"first": first, "now": now}, ensure_ascii=False)
    )
    for r in rows:
        print(
            f"{r['name']}: 정답 {r['pass_rate'] * 100:.0f}% · 출처 단 문장 {r['cited']} · 심판 지지 {r['supported']} · "
            f"${r['cost_per_q']}/문항 · p50 {r['p50_s']}초 · p95 {r['p95_s']}초"
        )
    for t, name in (
        ("number", "숫자"),
        ("year_compare", "전년 대비"),
        ("cross_company", "회사 비교"),
        ("narrative", "서술"),
        ("fact", "사실"),
        ("none", "근거 없음"),
        ("refuse", "투자 권유"),
    ):
        a = [x for x in first if qs[x["id"]]["type"] == t]
        b = [x for x in now if qs[x["id"]]["type"] == t]
        print(
            f"  {name:5s} 처음 {sum(x['correct'] for x in a)}/{len(a)} → 지금 {sum(x['correct'] for x in b)}/{len(b)}"
        )
    print("성적표 화면: uv run python sec22/02_scoreboard.py → http://127.0.0.1:8800")


if __name__ == "__main__":
    main(IDS)
