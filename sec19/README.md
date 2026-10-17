# 19편 LangChain MCP 어댑터 — 내 서버를 LangGraph 에이전트에

## 파일
| 파일 | 내용 |
|---|---|
| `requirements.txt` | 어댑터 전용 환경(실습 `.venv`의 mcp 2.3과 섞지 않는다): langchain-mcp-adapters **0.3.2**(mcp<2) · langchain · langchain-openai · langgraph · numpy |
| `env.py` | `.env` 읽기 · 모델(Flash) · 서버 설정 `DART`(어댑터가 `uv run -q python sec16/server_sdk.py`로 16편 SDK 서버를 실습 환경에서 띄운다) |
| `00_versions.sh` | 설치 세 가지: ① 0.3.2 + mcp 2.3 → 거절 ② 버전 없이 → 0.3.1이 깔리고 import 오류 ③ 전용 환경 |
| `01_adapter.py` | `MultiServerMCPClient` → `get_tools()`(MCP 도구 → LangChain 도구) → `create_agent`(LangGraph 그래프) → 질문 하나를 단계별로 |
| `02_session.py` | 기본(도구 호출마다 서버를 새로 띄움) vs `client.session()`으로 세션 유지 |
| `03_graph_mcp.py` | 14편 리서치 팀(그래프 · 프롬프트 그대로)의 재무 담당 · 공시 담당이 MCP 도구로 근거를 가져오게 바꾼다. 그래프 워커(스레드)와 비동기 MCP 도구는 `run_coroutine_threadsafe`로 잇는다 |

## 실행
```bash
zsh sec19/00_versions.sh
alias ad='uv run -q --no-project --with-requirements sec19/requirements.txt python'
ad sec19/01_adapter.py
ad sec19/02_session.py
ad sec19/03_graph_mcp.py
```
- `--no-project --with-requirements`: 실습 프로젝트 환경을 건드리지 않고, 이 목록으로 만든 따로 환경에서 실행한다(uv가 캐시해서 두 번째부터 바로 뜬다).
- 서버는 실습 환경(mcp 2.3), 어댑터 안의 클라이언트는 mcp 1.30이라 예전 방식(initialize)으로 말한다. 16편 SDK 서버가 dual-era라 그대로 받는다(16편 과제 3).

## 실제 결과 (2026-10-13 강의 녹화 실행, 모델 deepseek-v4-flash)
- 00_versions: ① "No solution found … langchain-mcp-adapters==0.3.2 depends on mcp>=1.24.0,<2.0.0" ② `adapters 0.3.1 · mcp 2.3.0` 설치 → `ImportError: cannot import name 'RequestContext' from 'mcp.shared.context'` ③ adapters 0.3.2 · mcp 1.30.0 · langgraph 1.2.15, 서버 쪽 mcp 2.3.0. (0.3.1은 2026-07-27, 상한 `mcp<2`는 0.3.2(2026-08-06)부터.)
- 01_adapter: 도구 3개 → LangChain 도구 1.7초, 그래프 `model → tools`. 모델이 get_financials · search_filings를 한 턴에 같이 골랐고 도구 결과 2.5초 · 3.3초(호출마다 서버를 띄움), 답 12.5초: 영업이익 732,036,535,379원(약 7,320억 원), 최대주주 김범수 13.28%(「VII. 주주에 관한 사항」).
- 02_session: 같은 도구 세 번 — 기본 2.6초(list_reports 0.43 · search_filings 1.76 · list_reports 0.45) vs 세션 유지 1.0초(0.02 · 0.98 · 0.01).
- 03_graph_mcp: "카카오 2025년 실적과 사업 위험 요인" → planner 3.3초(filings · financials) → 재무 담당 5.9초(근거 3) · 공시 담당 123.9초(근거 4, MCP 검색은 1.04초이고 나머지는 근거 추출 모델 호출) → writer 157.2초, 보고서 4문장, 근거 7개 모두 원문 대조 통과.

## 과제
1. 어댑터로 17편 원격 서버(HTTP + 토큰)에 붙는다.
2. 15편 서버와 16편 서버를 한 클라이언트에 같이 붙인다(도구 이름이 겹친다).
3. 도구 호출을 가로채서(인터셉터) 기록하고, 허용 목록 밖의 도구는 막는다.
