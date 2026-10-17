"""풀이 공통: sec07 모듈을 가져온다(파일 이름이 숫자로 시작해 import 문을 못 쓴다)."""

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("rag04", HERE / "04_rag.py")
rag04 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rag04)
