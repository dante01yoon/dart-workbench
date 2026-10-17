"""과제 2 풀이: 심판에게 같은 쌍을 세 번 물으면 판정이 얼마나 일치할까? 다수결로 정답률이 오를까?
사용: uv run --group frameworks python sec13/solutions/a2_self_consistency.py (02_eval.py를 먼저 돌린다)"""

import importlib
import io
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout

import _lab  # noqa: F401
from verify import judge

with redirect_stdout(io.StringIO()):
    cal = importlib.import_module("03_calibrate")
with ThreadPoolExecutor(8) as ex:
    votes = [list(ex.map(lambda c: judge(c[1], c[2])[0], cal.cases)) for _ in range(3)]
same = sum(len({v[i] for v in votes}) == 1 for i in range(len(cal.cases)))
once = sum(votes[0][i] == c[3] for i, c in enumerate(cal.cases))
major = sum((sum(v[i] for v in votes) >= 2) == c[3] for i, c in enumerate(cal.cases))
print(f"세 번 모두 같은 판정 {same}/{len(cal.cases)}")
print(f"한 번 물었을 때 정답 {once}/{len(cal.cases)} · 세 번 다수결 정답 {major}/{len(cal.cases)}")
