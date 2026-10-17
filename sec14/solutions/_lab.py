"""풀이 공통: sec14 · sec12 · sec10 모듈 경로를 잡고 프레임워크 경고를 끈다."""

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE.parent / "sec12", HERE.parent / "sec10"):
    sys.path.insert(0, str(p))
