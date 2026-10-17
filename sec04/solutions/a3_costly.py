"""과제 3 풀이: 어느 문항이 왜 비쌌나. data/context_runs.json에서 방식 B·C의 문항별 토큰과 도구 호출 순서를 본다.
사용: uv run python sec04/solutions/a3_costly.py   (01_context.py를 먼저 돌려 둔다)"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "sec02"))
from tools15 import ROOT

runs = json.loads((ROOT / "data" / "context_runs.json").read_text())
for key in ("B", "C"):
    print(f"■ {key} {runs[key]['label']}")
    for r in sorted(runs[key]["rows"], key=lambda r: -sum(r["calls"])):
        print(f"  {sum(r['calls']):7,} 토큰  {r['q']:<28} {' → '.join(r['tools'])}")
