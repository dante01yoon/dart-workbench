"""2편 ① 도구 15개 에이전트. 회사 이름을 줄여 말해도(예: "삼성") 인자 검사 → 오류 안내 → 고쳐 부르기로 복구한다.
사용: uv run python sec02/01_agent15.py "질문"
"""

import sys

from agent import run

q = " ".join(sys.argv[1:]) or "삼성 2025년 주당 배당금이랑 최대주주 지분율 알려줘"
print("질문:", q)
print("답:", run(q, verbose=True))
