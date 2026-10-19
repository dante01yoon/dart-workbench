"""29편 과제 3 — 루브릭 없이 "어느 답이 더 좋은가?"만 물으면? 같은 답 · 장황 쌍 12개를 순서 둘로 다시 묻는다.
사용: uv run python sec29/solutions/a3_no_rubric.py  (모델 호출 24번)
"""

import importlib
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
pw = importlib.import_module("02_pairwise")
pw.PAIR = """두 답 중 어느 답이 더 좋은가?
[질문] {q}
[근거]
{ev}
[답 1]
{a1}
[답 2]
{a2}
먼저 이유를 한두 문장으로 쓰고, 그다음 골라라. 둘이 같은 수준이면 "tie". JSON 하나로: {{"reason": "...", "winner": "1"}}"""

with ThreadPoolExecutor(6) as ex:
    res = list(ex.map(pw.judge_pair, [p for p in pw.pairs() if p["kind"] != "빠짐"]))
for r in res:
    print(f"  {r['id']} {r['kind']:5s} {r['runs'][0]['pick']:5s} / {r['runs'][1]['pick']}")
for k, v in pw.summary(res).items():
    if v["n"]:
        print(
            f"{k}: 순서 바꾸면 갈림 {v['flip']}/{v['n']} · "
            + ", ".join(f"{p} {n}" for p, n in v["picks"].items())
        )
print(f"호출 {2 * len(res)}번 · ${sum(run['cost'] for r in res for run in r['runs']):.4f}")
