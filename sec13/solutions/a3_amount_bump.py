"""과제 3 풀이: 03_calibrate의 '숫자 바꿈'은 첫 숫자를 바꿔서 대부분 연도(2025 → 5025)가 바뀌었다.
이번엔 금액만 10% 키운 쌍을 만들어 숫자 규칙과 심판을 다시 시험한다.
사용: uv run --group frameworks python sec13/solutions/a3_amount_bump.py (02_eval.py를 먼저 돌린다)"""

import importlib
import io
import re
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout

import _lab  # noqa: F401
from verify import AMOUNT, judge, numbers_ok

with redirect_stdout(io.StringIO()):
    cal = importlib.import_module("03_calibrate")


def bump_amount(claim):
    """첫 금액의 맨 앞 숫자 묶음을 10% 키운다. 금액이 없으면 None."""
    m = AMOUNT.search(claim)
    if not m:
        return None
    g = next(i for i in range(1, 6) if m.group(i))
    s, e = m.span(g)
    v = int(float(claim[s:e].replace(",", "")) * 1.1)
    return claim[:s] + f"{v:,}" + claim[e:]


pairs = [(bump_amount(c[1]), c[2]) for c in cal.cases if c[0] == "맞는 쌍"]
pairs = [p for p in pairs if p[0] and re.search(r"[조억원]", p[0])][:8]
with ThreadPoolExecutor(8) as ex:
    out = list(ex.map(lambda p: judge(*p), pairs))
print(
    f"금액 바꾼 쌍 {len(pairs)}개  숫자 규칙이 잡음 {sum(not numbers_ok(c, q) for c, q in pairs)}/{len(pairs)}"
    f" · 심판이 잡음 {sum(not o[0] for o in out)}/{len(pairs)}"
)
for (c, _), o in list(zip(pairs, out))[:3]:
    print(f"  {c[:60]} → {'지지' if o[0] else '부족'}")
