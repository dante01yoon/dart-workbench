"""1편 ③ 하네스와 성적표 v0 — 같은 문제 세트로 에이전트를 돌리고 통과율·토큰·비용·지연을 한 줄로 남긴다.

uv run python sec01/03_harness.py            # 숫자 문항 12개
uv run python sec01/scoreboard.py            # http://127.0.0.1:8800 성적표 화면
"""

import json
import os
import statistics
import sys
import time
import urllib.request

from tools import ROOT, TOOLS, get_financials

URL = os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions"
MODEL = os.environ.get("MODEL", "deepseek/deepseek-v4-pro")
SCORECARD = ROOT / "data" / "scorecard.jsonl"


class Trace:
    """실행 한 번의 기록: LLM 호출마다 토큰·비용·시간을 쌓는다."""

    def __init__(self):
        self.calls, self.tools = [], []

    def llm(self, messages):
        body = {
            "model": MODEL,
            "messages": messages,
            "tools": TOOLS,
            "usage": {"include": True},
        }
        req = urllib.request.Request(
            URL,
            data=json.dumps(body).encode(),
            headers={
                "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                "Content-Type": "application/json",
            },
        )
        t0 = time.time()
        r = json.load(urllib.request.urlopen(req, timeout=180))
        u = r.get("usage", {})
        self.calls.append(
            {
                "seconds": time.time() - t0,
                "tokens": u.get("total_tokens", 0),
                "cost": u.get("cost", 0),
            }
        )
        return r["choices"][0]["message"]


def run(question, trace, max_turns=6):
    messages = [{"role": "user", "content": question}]
    for _ in range(max_turns):
        reply = trace.llm(messages)
        messages.append(reply)
        if not reply.get("tool_calls"):
            return reply.get("content") or ""
        for call in reply["tool_calls"]:
            args = json.loads(call["function"]["arguments"])
            trace.tools.append(args)
            try:
                result = get_financials(**args)
            except Exception as e:
                result = {"error": str(e)}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    return ""


def flat(s):
    return "".join(s.split())


def main(name, types=("number",)):
    qs = [json.loads(line) for line in (ROOT / "eval" / "questions.jsonl").open(encoding="utf-8")]
    qs = [q for q in qs if q["type"] in types]  # 1편: 숫자 문항 12개(정답 = 재무 API 값)
    rows, traces = [], []
    for q in qs:
        tr, t0 = Trace(), time.time()
        answer = run(q["q"], tr)
        ok = any(flat(k) in flat(answer) for k in q["gold"]["contains"])
        rows.append({"id": q["id"], "ok": ok, "seconds": time.time() - t0})
        traces.append(tr)
        print(f"{'✅' if ok else '❌'} {q['q']:<34} {time.time() - t0:5.1f}s  도구 {len(tr.tools)}번")
    secs = sorted(r["seconds"] for r in rows)
    n = len(rows)
    row = {
        "name": name,
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "n": n,
        "pass_rate": round(sum(r["ok"] for r in rows) / n, 3),
        "tokens": sum(c["tokens"] for t in traces for c in t.calls),
        "cost_usd": round(sum(c["cost"] for t in traces for c in t.calls), 4),
        "cost_per_q": round(sum(c["cost"] for t in traces for c in t.calls) / n, 5),
        "p50_s": round(statistics.median(secs), 1),
        "p95_s": round(secs[min(n - 1, int(n * 0.95))], 1),
    }
    SCORECARD.parent.mkdir(exist_ok=True)
    with SCORECARD.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\n성적표 한 줄 → {SCORECARD.relative_to(ROOT)}")
    print(json.dumps(row, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else f"1편 · 루프 v0 · {MODEL.split('/')[-1]}"
    main(name, tuple(sys.argv[2].split(",")) if len(sys.argv) > 2 else ("number",))
