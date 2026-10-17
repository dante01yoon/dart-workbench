"""2편 ③ 같은 성적표에 둘째 줄: 도구 15개로 숫자 + 연도 비교 문항(20개)을 다시 잰다.
사용: uv run python sec02/03_harness15.py   → data/scorecard.jsonl에 한 줄 추가, sec01/scoreboard.py로 확인
"""

import json
import statistics
import sys
import time

from agent import MODEL, Trace, run
from tools15 import ROOT

SCORECARD = ROOT / "data" / "scorecard.jsonl"


def flat(s):
    return "".join(s.split())


def main(name, types=("number", "year_compare")):
    keys = json.loads((ROOT / "eval" / "answer_keys.json").read_text())
    qs = [json.loads(line) for line in (ROOT / "eval" / "questions.jsonl").open(encoding="utf-8")]
    qs = [q for q in qs if q["type"] in types]
    rows, traces = [], []
    for q in qs:
        tr, t0 = Trace(), time.time()
        answer = run(q["q"], tr)
        ok = all(any(flat(k) in flat(answer) for k in group) for group in keys[q["id"]])
        rows.append({"ok": ok, "seconds": time.time() - t0})
        traces.append(tr)
        used = ", ".join(sorted({n for n, _, _ in tr.tools}))
        print(f"{'✅' if ok else '❌'} {q['q']:<34} {time.time() - t0:5.1f}s  {used}")
    secs = sorted(r["seconds"] for r in rows)
    n = len(rows)
    cost = sum(c["cost"] for t in traces for c in t.calls)
    row = {
        "name": name,
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "n": n,
        "pass_rate": round(sum(r["ok"] for r in rows) / n, 3),
        "tokens": sum(c["tokens"] for t in traces for c in t.calls),
        "cost_usd": round(cost, 4),
        "cost_per_q": round(cost / n, 5),
        "p50_s": round(statistics.median(secs), 1),
        "p95_s": round(secs[min(n - 1, int(n * 0.95))], 1),
    }
    SCORECARD.parent.mkdir(exist_ok=True)
    with SCORECARD.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\n성적표 한 줄 → {SCORECARD.relative_to(ROOT)}\n{json.dumps(row, ensure_ascii=False, indent=1)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else f"2편 · 도구 15개 · {MODEL.split('/')[-1]}")
