# 2편 도구 설계 — 공시 조회 도구 15개

## 파일
| 파일 | 내용 |
|---|---|
| `tools15.py` | OpenDART API 15개를 도구로 감싼다. `SPEC` 표에 도구마다 이름·주소·인자 모양·좋은 설명·나쁜 설명·남길 칸. `run_tool`은 인자를 먼저 검사한다 |
| `agent.py` | 1편과 같은 에이전트 루프 + `Trace`(토큰·비용·시간 기록) |
| `01_agent15.py` | 도구 15개 에이전트에게 질문 하나 |
| `02_select.py` | 좋은 설명 vs 나쁜 설명: 질문 20개마다 맞는 도구를 첫 번에 고르는지 (도구는 실행하지 않음) |
| `03_harness15.py` | 1편 성적표에 둘째 줄: 숫자 + 연도 비교 20문항 |
| `04_validate.py` | 잘못된 인자를 넣었을 때 돌아오는 안내 |

## 실행
```bash
uv run python sec02/04_validate.py
uv run python sec02/01_agent15.py "카카오 2023년과 2025년 주당 배당금을 비교해 줘"
uv run python sec02/02_select.py
uv run python sec02/03_harness15.py
uv run python sec01/scoreboard.py
```

## 도구 15개
| 도구 | OpenDART | | 도구 | OpenDART |
|---|---|---|---|---|
| company_info | company | | largest_shareholder_changes | hyslrChgSttus |
| list_filings | list | | minority_shareholders | mrhlSttus |
| all_financial_statements | fnlttSinglAcntAll | | executives | exctvSttus |
| key_accounts | fnlttSinglAcnt | | employees | empSttus |
| compare_key_accounts | fnlttMultiAcnt | | executive_pay | hmvAuditIndvdlBySttus |
| financial_ratios | fnlttSinglIndx | | auditor_opinion | accnutAdtorNmNdAdtOpinion |
| dividends | alotMatter | | treasury_stock | tesstkAcqsDspsSttus |
| largest_shareholders | hyslrSttus | | | |

## 좋은 도구 설명의 네 가지
1. **무엇을 돌려주나**: "배당" 대신 "주당 현금배당금(원) · 배당성향(%) · 배당 총액"
2. **언제 쓰나**: 비슷한 도구가 여럿일 때 고르는 기준
3. **넣을 수 있는 값**: `Literal`(enum)로 회사 4곳, 연도 2024·2025
4. **긴 결과 거르기**: 재무제표 233줄 → `account="감가상각"`

여기에 하나 더: **도구 결과도 모델이 읽기 쉽게.** 칸 이름이 `thstrm`(당기)·`frmtrm`(전기)·`lwfr`(전전기)이면 모델이 연도를 한 해씩 밀려 읽는다.

## 녹화 때 실제 결과 (2026-10-11)
- 도구 선택 (qwen3.5-9b): 좋은 설명 20/20, 나쁜 설명 16/20. 대표이사 → `executives`, 직원 평균 연봉 → `executive_pay`처럼 이름이 비슷한 짝을 헷갈렸다. 다시 돌리면 나쁜 설명 쪽이 16~18개로 흔들린다.
- 성적표 (deepseek-v4-pro, 20문항): 90% · 243,473 토큰 · 문항당 $0.0036 · p50 12.9초 · p95 290.6초
  - 1편(80%)보다 올랐지만 토큰이 1편 12문항의 열 배를 넘는다. 연구개발비 두 문항에서 답할 도구가 없는데도 계정 이름을 바꿔 가며 헤맸다.
- 에이전트 답의 오류: "카카오 2023·2025 주당 배당금"에 2023년 60원, 2024년 61원이라고 답했다. 실제는 2023년 61원, 2024년 68원이다. → 과제 1

## 과제
1. 배당 도구 결과의 칸 이름을 실제 연도로 바꾸고, 카카오 질문을 다시 돌려 2024년이 68원으로 나오는지 확인한다.
2. 같은 도구를 같은 인자로 다시 부르면 막고, 턴 수에 상한을 둔다. 성적표에서 토큰과 p95가 얼마나 줄어드는지 잰다.
3. 증자·감자 현황 도구(`irdsSttus`)를 하나 더한다. 좋은 설명의 네 가지를 지킨다.

풀이: [SOLUTIONS.md](SOLUTIONS.md)
