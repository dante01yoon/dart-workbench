"""과제 1 풀이: 비용 상한이 실제로 멈추는지 — 상한을 아주 낮게($0.0005) 주고 리서치를 돌린다(서버가 8790에 떠 있어야 한다).
uv run python sec20/solutions/a1_budget.py
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
subprocess.run(
    [sys.executable, str(HERE / "01_stream.py"), "카카오 2025년 실적과 사업 위험 요인을 정리해 줘", "0.0005"],
    check=True,
)
