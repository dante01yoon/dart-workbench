# 16편 과제 풀이 (실측 2026-10-13)

## 과제 1 — 서버 안내문 · 도구 설명 (`solutions/a1_descriptions.py`, `tools_n.py`의 `BETTER_DESC`)
- 안내문에 "대표 숫자는 key_accounts, 대표이사 · 본사 주소는 company_info, 비율은 financial_ratios, 세부 계정만 all_financial_statements"를 적고, 세 도구 설명 끝에 쓰임새 한 줄씩을 붙였다.
- 도구 40개 · 도구 검색 켬, 질문 20개: 그대로 17/20(첫 입력 6,576토큰, 평균 3.1턴) → 고친 뒤 **20/20**(6,655토큰, 3.3턴). 토큰은 79개 늘었다.
- 고치기 전 틀린 것: "카카오 본사 주소" → 도구 없이 답, "SK하이닉스 2025년 영업이익" · "현대자동차 자산총계" → all_financial_statements.

## 과제 2 — SDK 클라이언트 (`solutions/a2_sdk_client.py`)
- `ClientSession.discover()` → 버전 2026-07-28, 도구 3개, 리소스 4개(현대자동차 목차 첫 줄 "I. 회사의 개요 > 1. 회사의 개요"), 프롬프트 첫 줄 "삼성전자와 SK하이닉스의 2025 사업보고서로 '수익성과 위험 요인'을 비교해 줘.", `get_financials(SK하이닉스)`.
- 함정: `s.initialize()`를 부르면 예전 핸드셰이크(2025-11-25)로 붙는다. 새 방식은 `s.discover()`.
- 15편 손 구현 서버에도 그대로 붙었다(도구만 있으니 리소스 · 프롬프트는 건너뜀).

## 과제 3 — 예전 클라이언트 → SDK 서버 (`solutions/a3_legacy_vs_sdk.py`)
- SDK 서버의 discover는 2026-07-28만 알려 주지만, `initialize`(2025-11-25)로 온 예전 클라이언트도 받아서 `_meta` 없이 tools/list · tools/call이 통했다(dual-era).
- 차이: 손 구현은 예전 방식 연결에도 새 방식 결과 틀(`resultType` · `_meta`)을 붙여 보냈고, SDK는 시대에 맞는 모양(`tools`만)으로 답했다.
