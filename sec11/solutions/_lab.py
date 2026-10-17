"""풀이 공통: sec11 모듈 경로를 잡고 프레임워크 경고를 끈다."""

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
