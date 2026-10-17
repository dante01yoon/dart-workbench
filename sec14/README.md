# 14편 LangGraph로 옮기기 — 이어서 돌기와 사람 승인

## 파일
| 파일 | 내용 |
|---|---|
| `graph.py` | 12편 팀을 상태 그래프로: planner → approve(interrupt) → worker × N(Send로 병렬) → writer. 근거는 `Annotated[list, operator.add]`로 이어 붙인다. 워커 · 프롬프트는 12편 Team 그대로 |
| `01_graph.py` | 그래프 모양(Mermaid) + 질문 하나를 단계별로(stream) |
| `02_resume.py` | SQLite 체크포인트(`data/lg_checkpoints.sqlite`)로 이어서 돌기: 뉴스 워커를 일부러 죽이고 같은 thread_id로 다시 |
| `03_approve.py` | 사람 승인: 계획을 보고 뺄 작업(번호 또는 종류 filings · news)을 입력 → `Command(resume=…)` |
| `04_compare.py` | 직접(12편) vs LangGraph: 흐름 코드 줄 수, 질문 3개의 시간 · 근거 · 출처 → `data/lg_compare.json` |
| `05_graph_web.py` | 그래프 · 비교 화면 http://127.0.0.1:8814 |

## 실행
```bash
uv run --group frameworks python sec14/01_graph.py
uv run --group frameworks python sec14/02_resume.py
uv run --group frameworks python sec14/03_approve.py
uv run --group frameworks python sec14/04_compare.py
uv run --group frameworks python sec14/05_graph_web.py
```
버전(녹화): langgraph 1.2.14 · langgraph-checkpoint-sqlite 3.1.2.

## 실제 결과 (2026-10-13 강의 녹화 실행)
- 01: planner 6.8초 → 재무 워커 9.3초 · 뉴스 워커 95.5초 → writer 126.9초, 보고서 6문장(12편과 같은 결과).
- 02: 첫 실행에서 뉴스 워커가 죽음 → 그때 돈 워커는 재무 하나, 저장된 상태의 다음 단계 `['worker']`. 같은 thread_id로 `invoke(None)` → 뉴스 워커만 다시 돌고(계획 · 재무는 다시 안 돎) 근거 7개 · 보고서 6문장.
- 03: 계획 4개(재무 · 공시 × 2개사) 중 `filings`를 빼니 t2 · t4가 빠지고, 보고서는 재무 숫자만 쓰고 위험 요인은 "확인되지 않습니다"라고 적었다.
- 04: 흐름 코드 줄 수 직접 75 · LangGraph 65.

| 질문 | 직접 | LangGraph |
|---|---|---|
| 카카오 | 139초 · 근거 7 · 4/4 | 440초 · 근거 7 · 4/4 |
| 삼성전자 vs SK하이닉스 | 112초 · 근거 14 · 5/5 | 52초 · 근거 14 · 6/6 |
| 현대자동차 | 215초 · 근거 7 · 6/6 | 77초 · 근거 7 · 6/6 |

  워커 · 모델이 같아서 시간 차이는 모델 응답이 흔들린 몫이다. 이 표로 어느 쪽이 빠르다고 말할 수 없다.
- 녹화 중 한 번은 03(승인 뒤 이어 돌기)이 15분 넘게 멈췄다(원인은 확인하지 못했다. 보고서도 출력되지 않았다). 오래 도는 에이전트에는 체크포인트만큼 시간 제한 · 재시도가 필요하다(과제 1).

## 과제
1. 워커 노드에 `RetryPolicy`를 붙여 한 번 실패한 워커를 그래프가 다시 부르게 한다.
2. writer 뒤에 13편 심판을 verify 노드로 붙인다.
3. writer 앞에 두 번째 interrupt를 두고 사람이 근거를 골라 뺀다.

풀이: [SOLUTIONS.md](SOLUTIONS.md)
