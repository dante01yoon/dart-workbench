"""과제 1 풀이: 배당 결과의 칸 이름(thstrm·frmtrm·lwfr)을 실제 연도로 바꾼다.
모델이 '당기·전기·전전기'를 한 해씩 밀려 읽던 문제를 도구 결과 설계로 고친다.
사용: uv run python sec02/solutions/a1_year_labels.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tools15
from agent import run

_orig = tools15.run_tool


def run_tool(name, args):
    r = _orig(name, args)
    if name == "dividends" and "rows" in r:
        y = int(args["year"])
        labels = {"thstrm": f"{y}년", "frmtrm": f"{y - 1}년", "lwfr": f"{y - 2}년"}
        r["rows"] = [{labels.get(k, k): v for k, v in row.items()} for row in r["rows"]]
    return r


tools15.run_tool = run_tool
import agent

agent.run_tool = run_tool
q = "카카오 2023년과 2025년 주당 배당금을 비교해 줘"
print("질문:", q)
print("답:", run(q, verbose=True))
