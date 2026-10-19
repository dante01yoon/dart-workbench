"""29편 과제 2 — 보수적 집계: 두 순서 모두에서 같은 답을 골랐을 때만 승, 갈리면 무승부(Zheng et al. 2023, MT-Bench).
저장된 data/pair29.json만 읽는다(모델 호출 없음).
사용: uv run python sec29/solutions/a2_conservative.py
"""

import json
from collections import Counter
from pathlib import Path

res = json.loads((Path(__file__).resolve().parents[2] / "data" / "pair29.json").read_text())["res"]
for kind in ("빠짐", "같은 답", "장황"):
    rs = [r for r in res if r["kind"] == kind]
    once = Counter(r["runs"][0]["pick"] for r in rs)  # 한 순서로만 물었을 때
    both = Counter(
        r["runs"][0]["pick"] if r["runs"][0]["pick"] == r["runs"][1]["pick"] else "무승부(갈림)" for r in rs
    )
    print(f"{kind:4s} 한 번만: {dict(once)}  →  두 순서 일치만 인정: {dict(both)}")
