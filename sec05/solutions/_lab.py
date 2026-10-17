"""풀이 공통: 01_long_task.py를 가져온다(파일 이름이 숫자로 시작해 import 문을 못 쓴다)."""

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("long_task", HERE / "01_long_task.py")
lt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lt)


def show(label, r):
    print(
        f"{label:22s} 정답 {r['cells']:2d}/{r['of']}  턴 {r['turns']:2d}  총 입력 {r['total_prompt_tokens']:7,d}  "
        f"최대 {r['peak_prompt_tokens']:6,d}  ${r['cost']:.4f}",
        flush=True,
    )
