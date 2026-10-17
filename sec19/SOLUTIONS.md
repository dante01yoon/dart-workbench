# 19편 과제 풀이 (실측 2026-10-13, 어댑터 전용 환경: langchain-mcp-adapters 0.3.2 · mcp 1.30.0 · langchain 1.4.4 · langgraph 1.2.14 — 녹화 날 다시 받으니 1.2.15)

## 과제 1 — 원격 서버(HTTP + 토큰)에 어댑터로 붙기 (`solutions/a1_remote_http.py`)
- 연결 설정만 바뀐다: `{"transport": "streamable_http", "url": …, "headers": {"Authorization": "Bearer …"}}`. 토큰은 `.env`의 `MCP_TOKEN_REMOTE`, 출력하지 않는다.
- 17편 배포 서버: 도구 `list_reports · get_financials · search_report` 0.9초, "현대자동차 2025년 매출과 최대주주" → get_financials + search_report, 8.0초. 매출 186,254,472,000,000원, 최대주주 현대모비스(주) 22.36%(「VII. 주주에 관한 사항」).
- 어댑터 안의 mcp 1.30 클라이언트는 예전 방식(initialize)으로 말하는데, mcp 2.3 서버가 HTTP에서도 dual-era라 그대로 붙었다.

## 과제 2 — 서버 두 개를 한 클라이언트에 (`solutions/a2_two_servers.py`)
- 15편 손 구현 서버(manual)와 16편 SDK 서버(sdk)를 같이 붙이면 도구 6개 중 이름이 3쌍 겹친다(`list_reports` · `get_financials` · `search_filings`).
- `tool_name_prefix=True` → `manual_get_financials` · `sdk_get_financials`처럼 서버 이름이 앞에 붙어 겹침 0. (Claude Code는 처음부터 `mcp__서버__도구`로 붙인다.)

## 과제 3 — 호출 가로채기(인터셉터) (`solutions/a3_interceptor.py`)
- `tool_interceptors=[guard]`: 부르기 전에 이름을 보고 허용 목록 밖이면 서버로 보내지 않고 오류 결과를 돌려준다. 걸린 시간도 기록.
- 허용 목록에서 `list_reports`를 빼고 "목록을 먼저 확인하고 SK하이닉스 2025년 영업이익" → 기록 `막음 list_reports · 막음 list_reports · get_financials(SK하이닉스) 3.73초`. 답은 영업이익 47,206,319,000,000원, 그리고 목록 도구가 허용되지 않았다고 밝혔다.
- 18편 guard(중계 서버)와 같은 방어를 어댑터 안에서 하는 방법이다.
