"""풀이 공통: 01_context.py의 run_strategy·report를 가져온다(파일 이름이 숫자로 시작해 import 문을 못 쓴다)."""

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("context", HERE / "01_context.py")
ctx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctx)
