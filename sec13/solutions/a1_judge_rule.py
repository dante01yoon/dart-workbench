"""과제 1 풀이: 심판 지시문에서 "숫자는 단위만 바꾼 것은 같은 값" 규칙을 빼면? 03_calibrate와 같은 쌍으로 다시 잰다.
사용: uv run --group frameworks python sec13/solutions/a1_judge_rule.py (02_eval.py를 먼저 돌린다)"""

import importlib
import io
from contextlib import redirect_stdout

import _lab  # noqa: F401
import verify

with redirect_stdout(io.StringIO()):
    cal = importlib.import_module("03_calibrate")  # 같은 쌍(cases)을 그대로 쓴다
base = verify.JUDGE
for label, prompt in (
    ("본편 지시문", base),
    ("단위 규칙 뺌", "\n".join(ln for ln in base.splitlines() if "단위만" not in ln)),
):
    verify.JUDGE = prompt
    out = [verify.judge(c[1], c[2]) for c in cal.cases]
    line = f"{label:8s}"
    for kind in ("맞는 쌍", "숫자 바꿈", "인용 바꿈"):
        idx = [i for i, c in enumerate(cal.cases) if c[0] == kind]
        line += f"  {kind} {sum(out[i][0] == cal.cases[i][3] for i in idx)}/{len(idx)}"
    print(line, flush=True)
