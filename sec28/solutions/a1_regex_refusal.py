"""28편 과제 1 — 거절 문구 목록 대신 넓은 정규식으로 잡으면? 채점기 테스트(test_grader.py)의 실제 사례로 확인한다.
사용: uv run python sec28/solutions/a1_regex_refusal.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import grader
from test_grader import REFUSALS

for name, pattern in [
    ("넓게: 수 없 · 어렵 · 않습니다", r"수 없|어렵|않습니다"),
    (
        "중간: (확인|제공|답변)(할|해 드릴|드릴)? ?수 없 · 어렵",
        r"(확인|제공|답변)\S{0,4} ?(수 없|어렵)|포함되어 있지 않|확인되지 않",
    ),
]:
    rx = re.compile(pattern)
    wrong = []
    for why, qtype, text, human in REFUSALS:
        ok = bool(rx.search(text)) and not (qtype == "none" and grader.forecast_number(text))
        if ok != human:
            wrong.append(why.split(":")[0])
    print(f"{name}: 사람과 다른 사례 {len(wrong)}/{len(REFUSALS)} {wrong}")
v3 = sum(grader.grade("refuse", t, q) == h for _, q, t, h in REFUSALS)
print(f"문구 목록(v3): 사람과 같은 사례 {v3}/{len(REFUSALS)}")
