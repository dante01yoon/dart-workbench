"""30편 과제 3 — 불일치를 읽고 판사를 고친다. 29편 R6 판사는 근거의 요약(claim)만 봤다. 원문 인용(quote)까지 주면
넣은 문장은 여전히 잡고, 원본의 '아니오' 3개(q17 · n10 · q49)는 사라지나?
사용: uv run python sec30/solutions/a3_judge_with_quote.py  (모델 호출 16번, 약 $0.01) → data/judge30_quote.json
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sec29"))
from judge import TRACES, ask, evidence, prompt_v2  # 29편 판사 v2 그대로

FAKE = __import__("importlib").import_module("01_judge").FAKE  # 29편에서 넣은 문장


def quoted(x):
    return "\n".join(
        f"{e['id']} [{e['source']}] 요약: {e['claim']} / 원문: {e.get('quote', '')}" for e in x["evidence"]
    )


def run(job):
    qid, fake = job
    x = TRACES[qid]
    rep = x["report"] + ([{"sentence": FAKE[qid][0], "cites": [FAKE[qid][1]]}] if fake else [])
    v, c = ask(prompt_v2("R6", x, rep).replace(evidence(x), quoted(x)))  # 바뀐 곳은 [근거] 칸 하나
    return {"id": qid, "fake": fake, "one": v.get("pass"), "why": v.get("reason", ""), "cost": c}


with ThreadPoolExecutor(6) as ex:
    res = list(ex.map(run, [(q, f) for q in FAKE for f in (False, True)]))
old = {(r["id"], r["fake"]): r["one"] for r in json.loads((ROOT / "data" / "judge29.json").read_text())["b"]}
print("문항  넣은 문장  요약만(29편)  원문까지")
for r in res:
    print(
        f"  {r['id']}  {'예' if r['fake'] else '-':4s}  {old[(r['id'], r['fake'])]!s:6s}  {r['one']!s:6s}  {r['why'][:60]}"
    )
caught = sum(r["one"] is False for r in res if r["fake"])
flagged = [r["id"] for r in res if not r["fake"] and r["one"] is False]
print(
    f"넣은 문장 잡음 {caught}/8 · 원본에 '아니오' {len(flagged)}/8 {flagged} · 비용 ${sum(r['cost'] for r in res):.4f}"
)
(ROOT / "data" / "judge30_quote.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
