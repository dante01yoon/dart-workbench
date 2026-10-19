"""28편 과제 2 — q49(카카오 플랫폼 부문 구성) 정답 키 "톡비즈" 한 낱말을 조이면 무엇이 바뀌나. 저장된 답만 다시 채점한다.
사용: uv run python sec28/solutions/a2_tighten_q49.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "sec28"))
import grader

OLD = [["톡비즈"]]
NEW = [
    ["톡비즈"],
    ["포털비즈", "플랫폼기타", "플랫폼 기타"],
]  # 공시: 플랫폼 부문 = 톡비즈 · 포털비즈 · 플랫폼 기타


def rep(x):
    return " ".join(s["sentence"] for s in x["report"])


rows = [
    ("22편 처음", x["answer"])
    for x in json.loads((ROOT / "data/final_eval.json").read_text())["first"]
    if x["id"] == "q49"
]
rows += [
    ("22편 지금", rep(x))
    for x in json.loads((ROOT / "data/final_eval.json").read_text())["now"]
    if x["id"] == "q49"
]
rows += [
    (f"10/18 {x['round']}회", x["answer"])
    for x in json.loads((ROOT / "data/repeat3_1018.json").read_text())
    if x["id"] == "q49"
]
rows += [("26편", rep(x)) for x in map(json.loads, (ROOT / "data/traces26.jsonl").open()) if x["id"] == "q49"]
for name, text in rows:
    print(
        f"{name:9s} 키 그대로 {'✅' if grader.grade(OLD, text) else '❌'} → 조인 키 {'✅' if grader.grade(NEW, text) else '❌'}  {text[:60]!r}"
    )
