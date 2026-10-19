"""34편 과제 3 풀이 — 이력서 문장 검사기: 부풀린 문장을 코드로 걸러 본다. 모델 호출 0.

세 가지를 본다.
  1. 숫자 출처: 문장의 숫자(%, 분수, 개수)가 기록(23~34편 README · data/compare34.json)에 있나
  2. 분모: 비율(%)을 말하면 같은 문장에 몇 개 중인지(N/M · N문항 · N개)가 있나
  3. 막연한 말: "대규모 · 획기적 · 크게 · 업계 최고" 같은 말 대신 무엇을 막았는지가 있나
사용: uv run python sec34/solutions/a3_resume_check.py
"""

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
spec = importlib.util.spec_from_file_location("pf", ROOT / "sec34" / "04_portfolio.py")
pf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pf)  # GOOD · BAD 문장과 README(화면은 띄우지 않는다)

EVIDENCE = "\n".join((ROOT / f"sec{n}" / "README.md").read_text() for n in range(23, 34)) + pf.README
EVIDENCE += json.dumps(json.loads((ROOT / "data" / "compare34.json").read_text()))
VAGUE = ["대규모", "획기적", "크게", "업계 최고", "완벽", "대폭"]
NUM = re.compile(r"\d+(?:\.\d+)?(?:/\d+|%|문항|개)")


def check(s):
    probs = [f"기록에 없는 숫자 {n}" for n in NUM.findall(s) if n not in EVIDENCE]
    if "%" in s and not re.search(r"\d+/\d+|\d+문항|\d+개", s):
        probs.append("비율만 있고 분모가 없다")
    probs += [f"막연한 말 '{w}'" for w in VAGUE if w in s]
    return probs


for name, xs in (("쓸 문장", pf.GOOD), ("쓰지 않을 문장", [a for a, _ in pf.BAD])):
    print(name)
    for s in xs:
        p = check(s)
        print(f"  {'통과' if not p else '걸림'}  {s[:46]}…" + ("" if not p else "  ← " + " · ".join(p)))
