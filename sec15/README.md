# 15편 MCP 서버 손으로 만들기 — Claude Code에서 공시 검색

## 파일
| 파일 | 내용 |
|---|---|
| `server.py` | 표준 라이브러리만으로 만든 MCP 서버(stdio, 한 줄 JSON-RPC). 2026-07-28(요청마다 `_meta` 버전) + 예전 `initialize`(2025-11-25)를 둘 다 받는다. 도구 3개: `list_reports` · `get_financials`(2편 재무 API) · `search_filings`(10편 맥락 하이브리드 검색). `NO_CACHE_FIELDS=1`이면 목록 결과의 캐시 필드(`ttlMs` · `cacheScope`)를 일부러 뺀다. `MCP_TRACE`에 파일 경로를 주면 오간 메시지를 남긴다 |
| `mcp.json` | Claude Code 설정(서버 띄우는 명령 + `MCP_TRACE=data/mcp_trace.jsonl`) |
| `mcp_nocache.json` | 캐시 필드를 뺀 서버 설정(실험용) |
| `01_talk.py` | 우리가 클라이언트가 되어 서버를 띄우고 discover → tools/list → tools/call ×2 → 모르는 버전을 한 줄씩 주고받는다. 인자로 다른 서버 파일을 줄 수 있다(16편) |
| `02_trace.py` | `MCP_TRACE` 기록을 순서대로 보여 준다 |

## 실행
```bash
uv run python sec15/01_talk.py
claude --strict-mcp-config --mcp-config sec15/mcp_nocache.json --model haiku --tools ""
uv run python sec15/02_trace.py data/mcp_trace_nocache.jsonl
claude --strict-mcp-config --mcp-config sec15/mcp.json --model haiku --tools ""
uv run python sec15/02_trace.py data/mcp_trace.jsonl
```
- `--strict-mcp-config`: 이 설정 파일의 서버만 쓴다(내 다른 MCP 서버는 빼고). `--tools ""`: Claude Code 기본 도구(파일 읽기 · 셸 · 웹 검색)를 꺼서 우리 서버 도구만 쓰게 한다.
- 처음 여는 폴더면 "이 폴더를 믿느냐"는 창이 한 번 뜬다.
- 녹화 화면에서는 개인 설정(`~/.claude/settings.json`)을 읽지 않게 `--setting-sources project`를 셸 함수로 붙였다.

## 개념 출처
- Anthropic, "Introducing the Model Context Protocol"(2024-11-25) · "Donating the Model Context Protocol and establishing the Agentic AI Foundation"(2025-12-09, 리눅스 재단 산하)
- MCP 규격 2026-07-28: Versioning(핸드셰이크 없음, 요청마다 `_meta`에 버전 · `UnsupportedProtocolVersionError` -32022 · dual-era), Discovery(`server/discover` 필수), 목록 결과의 캐시 필드
- 공식 문서의 비유: "AI 앱의 USB-C 포트"

## 실제 결과 (2026-10-13 강의 녹화 실행, Claude Code 2.1.296 · Haiku 5.5)
- 01_talk: discover 0.9초(지원 버전 3개), 도구 3개, `get_financials(현대자동차)` 2.5초 — 매출액 186,254,472,000,000원 · 영업이익 11,467,851,000,000원, `search_filings('관세 위험')` 2.3초 — 세 조각 모두 「III. 재무에 관한 사항 > 34. 위험관리 (연결)」, 모르는 버전(2024-11-05) → -32022.
- 캐시 필드를 뺀 서버: "현대차 위험 요인 찾아줘"에 "찾아보겠습니다"만 말하고 도구를 하나도 부르지 못한 채 5초 만에 끝났다. `/mcp` 화면: `dart  tools fetch failed · connected`. 서버 기록: discover 1번 · tools/list 4번 · tools/call 0번. 질문할 때는 경고가 없었다.
- 고친 서버: dart 도구 3번(모두 `search_filings`, k=8, 결과 7,041 · 6,995 · 7,376자), 답 21초, 문장마다 섹션 경로 출처. 서버 기록: discover 1 · tools/list 1 · tools/call 3.
- 녹화 전 시험(같은 날): 캐시 필드가 없을 때 Claude Code가 모델의 기억으로 답한 적도 있다("제가 가진 지식을 바탕으로"). 어느 쪽이든 도구는 쓰지 못했다.

## 과제
1. 기업 개황 도구 `company_info`를 붙이고 Claude Code에 "카카오 대표이사가 누구야?"를 묻는다.
2. 예전 클라이언트(2025-11-25)처럼 `initialize` → `notifications/initialized` → `tools/list` → `tools/call`로 붙어 본다.
3. 지원하지 않는 회사 이름(LG전자)이 오면 빈 결과 대신 `isError` 결과로 알려 준다.
