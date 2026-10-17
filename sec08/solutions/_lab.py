"""풀이 공통: sec08 모듈 경로를 잡는다."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
