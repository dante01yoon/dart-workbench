"""과제 3 풀이: 도구 설명을 일부러 나쁘게 바꾸면 성적표가 어떻게 변하나 (2편 예고).

나쁜 설명 = 무엇을 돌려주는지, 어떤 값을 넣어야 하는지 알 수 없는 설명.
  - description: "데이터"
  - corp: enum 없음(회사 이름 철자를 모델이 마음대로 씀), year: 설명 없음
사용: uv run python sec01/solutions/a3_bad_description.py
"""

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import tools

tools.TOOLS[0]["function"]["description"] = "데이터"
tools.TOOLS[0]["function"]["parameters"]["properties"] = {
    "corp": {"type": "string"},
    "year": {"type": "integer"},
}

spec = importlib.util.spec_from_file_location("harness", HERE / "03_harness.py")
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
harness.main(f"과제3 · 나쁜 도구 설명 · {harness.MODEL.split('/')[-1]}")
