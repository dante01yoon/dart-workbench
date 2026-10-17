"""13편 ③ 심판도 시험한다: 맞는 쌍과 일부러 망가뜨린 쌍을 섞어 심판(LLM)과 숫자 규칙의 정확도를 잰다.
- 맞는 쌍: ② 평가에서 팀이 모은 근거 중 원문 일치를 통과한 {claim, quote}
- 숫자 바꿈: claim의 첫 숫자 한 자리를 바꾼 것
- 인용 바꿈: claim에 다른 회사 · 다른 근거의 quote를 붙인 것
사용: uv run --group frameworks python sec13/03_calibrate.py (② 02_eval.py를 먼저 돌린다)"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec12"))  # 12편 팀 → sec10 → sec07
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec10"))
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor

from verify import judge, numbers_ok
from web import ROOT

random.seed(7)
rows = json.loads((ROOT / "data" / "team_eval.json").read_text())
ev = [e for r in rows for e in r.get("evidence", []) if e.get("verified") and re.search(r"\d", e["claim"])]
ev = list({e["claim"]: e for e in ev}.values())
random.shuffle(ev)
pos = ev[:16]


def bump(claim):
    m = re.search(r"\d", claim)
    d = str((int(m.group(0)) + 3) % 10 or 7)
    return claim[: m.start()] + d + claim[m.end() :]


cases = [("맞는 쌍", e["claim"], e["quote"], True) for e in pos]
cases += [("숫자 바꿈", bump(e["claim"]), e["quote"], False) for e in pos[:8]]
others = ev[16:] or ev
cases += [
    ("인용 바꿈", e["claim"], next(o["quote"] for o in others if o["source"] != e["source"]), False)
    for e in pos[8:16]
]

with ThreadPoolExecutor(8) as ex:
    out = list(ex.map(lambda c: judge(c[1], c[2]), cases))
print(f"{'종류':6s} {'수':>3s}  심판 정답  숫자 규칙 정답")
for kind in ("맞는 쌍", "숫자 바꿈", "인용 바꿈"):
    idx = [i for i, c in enumerate(cases) if c[0] == kind]
    j = sum(out[i][0] == cases[i][3] for i in idx)
    r = sum(numbers_ok(cases[i][1], cases[i][2]) == cases[i][3] for i in idx)
    print(f"{kind:6s} {len(idx):3d}  {j:3d}/{len(idx)}    {r:3d}/{len(idx)}")
miss = [(c, o) for c, o in zip(cases, out) if o[0] != c[3]]
for c, o in miss[:3]:
    print(f"  틀린 판정 · {c[0]} · {c[1][:50]} → {'지지' if o[0] else '부족'} ({o[1][:50]})")
print(f"심판 비용 ${sum(o[2] for o in out):.4f}")
