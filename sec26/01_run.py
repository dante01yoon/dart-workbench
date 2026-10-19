"""26편 ① 개발 문항을 돌리며 단계마다 기록(트레이스)을 남긴다 — 오류 분석의 재료.

- 문항: 시험지 v2의 개발 48문항(held-out은 열지 않는다) + 24편에서 틀린 처음 보는 문항 5개.
- 워크벤치(20편)가 내보내는 이벤트를 그대로 모은다: 계획 → 작업(공시 · 재무 · 뉴스) → 근거 → 작성 → 심판 → 반성.
- 채점은 22편 채점기 그대로(정답 낱말 · 거절 문구). 채점기가 틀렸는지는 2단계에서 사람이 읽고 적는다.
사용: uv run python sec26/01_run.py          → data/traces26.jsonl
      uv run python sec26/01_run.py n15 q38  → 고른 문항만(data/traces26_try.jsonl, 비용 미리 재기)
"""

import importlib.util
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("final", ROOT / "sec22" / "01_final_scorecard.py")
final = importlib.util.module_from_spec(spec)
spec.loader.exec_module(final)  # 22편 채점기(grade) · 워크벤치 · MCP 연결

V2 = [json.loads(line) for line in (ROOT / "eval" / "questions_v2_locked.jsonl").open()]
DEV = [x for x in V2 if x["split"] == "dev"]  # held-out은 큰 결정 때만 연다
MISSED24 = ["q32", "q33", "q38", "q50", "q52"]  # 24편 처음 보는 문항 중 틀린 것
ITEMS = DEV + [
    {"id": i, "q": final.qs[i]["q"], "type": final.qs[i]["type"], "keys": final.ks[i]} for i in MISSED24
]


def grade(keys, text, refused):
    final.ks["_"] = keys  # 22편 grade는 id로 정답 키를 찾는다
    return final.grade("_", text, refused)


def run(item):
    events, t0 = [], time.time()
    wb = final.Workbench(final.mcp, emit=events.append, cap=0.05)
    try:
        r = wb.research(item["q"])
    except final.BudgetExceeded:
        r = {"refused": False, "report": [], "evidence": []}
        events.append({"type": "budget"})
    rep = r.get("report", [])
    text = " ".join(s["sentence"] for s in rep) + " " + " ".join(e["claim"] for e in r.get("evidence", []))
    out = {
        **{k: item[k] for k in ("id", "q", "type", "keys")},
        "correct": grade(item["keys"], text, r.get("refused", False)),
        "refused": r.get("refused", False),
        "report": rep,
        "evidence": r.get("evidence", []),
        "events": events,
        "cost": round(wb.spent, 5),
        "seconds": round(time.time() - t0, 1),
    }
    print(
        f"{out['id']:4s} {'✅' if out['correct'] else '❌'} {out['seconds']:5.0f}초 ${out['cost']:.4f}  {summary(events)}",
        flush=True,
    )
    return out


def summary(events):
    """한 줄 궤적: 계획(작업 수) → 근거(확인된/뽑은) → 심판(지지/문장)"""
    plan = next((e for e in events if e["type"] == "plan"), None)
    if any(e["type"] == "refused" for e in events):
        return "계획에서 거절"
    if not plan:
        return "계획 실패"
    got = sum(e["n"] for e in events if e["type"] == "task_end")
    use = next((e["evidence"] for e in events if e["type"] == "writing"), 0)
    ver = [e for e in events if e["type"] == "verify"]
    judge = f"{ver[-1]['ok']}/{ver[-1]['total']}" if ver else "-"
    workers = "·".join(t["worker"][:3] for t in plan["tasks"])
    return f"계획 {len(plan['tasks'])}({workers}) → 근거 {use}/{got} → 심판 {judge}"


if __name__ == "__main__":
    pick = sys.argv[1:]
    items = [x for x in ITEMS if x["id"] in pick] if pick else ITEMS
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(run, items))
    final.mcp.close()
    path = ROOT / "data" / ("traces26_try.jsonl" if pick else "traces26.jsonl")
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in res))
    bad = [x["id"] for x in res if not x["correct"]]
    print(
        f"\n{len(res)}문항 · 채점기 정답 {len(res) - len(bad)} · 틀림 {len(bad)} · ${sum(x['cost'] for x in res):.4f}"
    )
    print("틀린 문항:", " ".join(bad))
    print(f"기록 → {path.relative_to(ROOT)}  · 다음: uv run python sec26/02_memo.py")
