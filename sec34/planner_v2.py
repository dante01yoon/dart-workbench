"""34편 개선 한 바퀴 — 바꾸는 곳은 딱 하나, 계획 담당 지시문(12편 PLANNER)이다.

26편 오류 분석에서 "처음 틀어진 단계"가 가장 많았던 칸이 계획(6개)이었다:
  재무 도구에 없는 숫자를 재무 조회에 맡김(n14 · q38), 연도를 잘못 잡음(q32),
  아직 공시되지 않은 미래를 뉴스로 찾아 사실처럼 답함(q51 · q52 · q54).
세 가지 모두 "도구가 못 하는 일을 계획했다"는 같은 원인이라, 지시문에 그 경계를 적는다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec12"))
from team import PLANNER  # 12편 계획 담당 지시문(v1)

ADDED = """도구가 못 하는 일은 계획하지 마라.
- financials는 매출액 · 영업이익 · 당기순이익 세 숫자만 준다. 재고자산 · 배당금 · 자본총계 · 연구개발비 같은 다른 숫자는 filings로 찾는다.
- 질문에 연도가 없으면 2025년(당기)과 2024년(전기)이다.
- 자료는 2025년 사업보고서까지다. 2026년 이후의 실적 · 전망 · 출시 일정처럼 아직 공시되지 않은 것을 물으면 tasks를 비우고 refuse를 true로. 뉴스 전망을 사실처럼 답하지 않는다."""

PLANNER_V2 = PLANNER.replace("JSON만:", ADDED + "\nJSON만:")
assert PLANNER_V2 != PLANNER and PLANNER_V2.count(ADDED) == 1  # 넣을 자리를 못 찾으면 바로 멈춘다

PLAN_FAILS = ["n14", "q38", "q32", "q51", "q52", "q54"]  # 26편 메모에서 처음 틀어진 단계 = 계획
