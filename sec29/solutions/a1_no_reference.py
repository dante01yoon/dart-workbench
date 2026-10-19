"""29편 과제 1 — 정답 정보를 빼면? R2 판사 v2에서 [정답 정보] 줄만 지우고(근거는 준다) 같은 14문항을 다시 채점한다.
사용: uv run python sec29/solutions/a1_no_reference.py  (모델 호출 14번)
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from judge import RB, ROOT, TRACES, ask, evidence, prompt_v2

saved = {r["id"]: r for r in json.loads((ROOT / "data" / "judge29.json").read_text())["a"]}


def no_ref(qid):
    x = TRACES[qid]
    p = prompt_v2("R2", x, x["report"])
    p = "\n".join(
        line if not line.startswith("[정답 정보]") else f"[근거]\n{evidence(x)}" for line in p.split("\n")
    )
    v, c = ask(p)
    return qid, v.get("pass"), c


with ThreadPoolExecutor(6) as ex:
    res = list(ex.map(no_ref, saved))
for qid, v, _ in res:
    code = bool(RB.RUBRIC[1][-1](TRACES[qid]))
    print(f"{qid}  코드 {code!s:5s} 정답 정보 있음 {saved[qid]['v2']!s:5s} 없음 {v!s:5s}")
same = sum(v == bool(RB.RUBRIC[1][-1](TRACES[q])) for q, v, _ in res)
print(
    f"코드와 같은 판정: 정답 정보 있음 {sum(r['v2'] == r['code'] for r in saved.values())}/14 · 없음 {same}/14"
)
print(f"호출 {len(res)}번 · ${sum(c for *_, c in res):.4f}")
