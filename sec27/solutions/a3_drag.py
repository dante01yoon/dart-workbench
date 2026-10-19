"""27편 과제 3 — "모두 통과" 비율을 가장 많이 끌어내리는 기준은? 기준을 하나씩 빼고 다시 센다.
사용: uv run python sec27/solutions/a3_drag.py
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("r", Path(__file__).resolve().parent.parent / "01_rubric.py")
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

coded = [(rid, name, fn) for rid, name, *_, fn in r.RUBRIC if fn]


def allpass(skip=None):
    return sum(all(fn(x) for rid, _, fn in coded if rid != skip and r.applies(rid, x)) for x in r.TRACES)


base = allpass()
print(f"모두 통과 {base}/{len(r.TRACES)}")
for rid, name, _ in coded:
    print(f"  {rid} {name} 빼면 {allpass(rid)}/{len(r.TRACES)} (+{allpass(rid) - base})")
