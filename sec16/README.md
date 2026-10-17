# 16편 공식 SDK로 다시 쓰기 — 리소스 · 프롬프트, 그리고 도구가 많을 때

## 파일
| 파일 | 내용 |
|---|---|
| `server_sdk.py` | 15편 서버를 공식 Python SDK(`mcp==2.3.0`, `MCPServer`)로. 도구는 데코레이터(입력 스키마는 타입 힌트, 설명은 docstring), 도구 본체는 15편 `call_tool`. 리소스: 회사마다 `dart://toc/<회사>`(보고서 목차). 프롬프트: `compare_companies(corp_a, corp_b, topic)` |
| `mcp.json` | Claude Code 설정(SDK 서버) |
| `01_compare.py` | 손 구현 vs SDK: 코드 줄 수 · 버전만 실은 `_meta`에 대한 반응 · discover 결과 |
| `tools_n.py` | 실험용 서버: 15편 서버에 3편 도구 15개(`TOOLS_N=15`) 또는 40개(`TOOLS_N=40`)를 MCP 도구로. `BETTER_DESC=1`이면 서버 안내문 · 도구 설명을 고친다(과제 1) |
| `03_tool_count.py` | 도구 15 · 40개 × Claude Code 도구 검색 켬 · 끔 × 3편 질문 20개를 `claude -p`로 → 고른 도구 · 첫 호출 입력 토큰 · 턴 · 시간 · 비용 → `data/cc_tool_count.json` |

## 실행
```bash
uv run python sec16/01_compare.py
claude --strict-mcp-config --mcp-config sec16/mcp.json --model haiku --tools "ListMcpResourcesTool,ReadMcpResourceTool"
#   @dart: → 회사 목차 고르기 → "이 목차에서 위험과 관련된 섹션만 골라줘"
#   /mcp__dart__compare_companies 삼성전자 SK하이닉스
uv run python sec16/03_tool_count.py      # claude -p 80번, 약 4~6분
```
- 리소스를 읽으려면 Claude Code 기본 도구 `ListMcpResourcesTool` · `ReadMcpResourceTool`이 켜져 있어야 한다. `--tools ""`로 다 끄면 `@`로 고른 리소스도 읽지 못했다("리소스를 직접 열 수 없어서").
- `@` 목록에서 고를 때는 방향키 + Enter. 한글로 걸러지지 않아서 Tab은 공통 앞부분(`dart://toc/`)만 채웠다.
- 프롬프트는 목록에 `/dart:compare_companies (MCP)`로 보이지만, 그 이름을 그대로 치면 "Unknown command"였다. `/mcp__dart__compare_companies`로 쳐야 했다(Claude Code 2.1.296).

## 개념 출처
- MCP 규격 2026-07-28 Server Overview 표: Prompts = User-controlled(슬래시 명령), Resources = Application-controlled(앱이 붙이는 맥락), Tools = Model-controlled
- Claude Code 문서 "Scale with MCP tool search": 도구 검색은 기본으로 켜져 있고, 처음엔 도구 이름(과 서버 안내문)만 싣고 필요할 때 정의를 불러온다. `ENABLE_TOOL_SEARCH`로 켜고 끈다. 서버 작성자는 안내문(instructions)으로 언제 도구를 찾을지 알려 준다.

## 실제 결과 (2026-10-13 강의 녹화 실행, Claude Code 2.1.296 · Haiku 5.5)
- 01_compare: 코드 176줄 → 46줄(ruff 포맷 뒤, docstring · 주석 · 빈 줄 제외. 도구 본체는 15편 것을 그대로 쓴다). `_meta`에 버전만 실은 요청: 손 구현은 받아 줌, SDK는 -32602 "params._meta is missing the required envelope key(s)"(클라이언트 정보 · 기능이 빠졌다). discover: 손 구현은 버전 3개 · 기능 [tools] · 캐시 public/300000, SDK는 버전 ['2026-07-28'] · 기능 [prompts, resources, tools] · 캐시 private/0.
- `@dart:dart://toc/현대자동차` + "위험과 관련된 섹션만": `readMcpResource` 한 번, 7초, 직접 관련 3개(II-5 위험관리 및 파생거래 · III-34 위험관리(연결) · III-32 위험관리) + 간접 관련 6개.
- `/mcp__dart__compare_companies 삼성전자 SK하이닉스`: dart 도구 6번, 28초, 항목 × 두 회사 표 하나, 칸마다 `[get_financials]` 또는 `[회사 · 섹션 경로]`.
- 03_tool_count (질문 20개씩, 4분 14초):

| 도구 | 도구 검색 | 맞은 도구 | 첫 호출 입력 토큰 | 평균 턴 | 평균 시간 | 비용(20문항) |
|---|---|---|---|---|---|---|
| 15 | 켬 | 19/20 | 4,766 | 3.1 | 11.4초 | $0.0226 |
| 15 | 끔 | 20/20 | 6,569 | 2.2 | 9.2초 | $0.0155 |
| 40 | 켬 | 18/20 | 5,116 | 3.2 | 12.7초 | $0.0229 |
| 40 | 끔 | 20/20 | 9,736 | 2.5 | 10.3초 | $0.0189 |

  - 도구 검색은 40개에서 첫 호출 입력을 47% 줄였지만(9,736 → 5,116), 찾는 턴이 하나 더 생겨 시간 · 비용은 늘었다. 틀린 3건은 모두 `company_info`를 못 찾은 경우(본사 주소 → 도구 없이 답, 대표이사 → `executives`).
  - 같은 날 녹화 전 실행(내 터미널): 40개 · 켬 16/20 · 6,575토큰, 40개 · 끔 19/20 · 11,195토큰. 녹화 셸(개인 설정 없음)에서는 첫 입력이 1~1.5천 토큰 적었다. 정답 수는 실행마다 1~3개씩 흔들린다.
- 결론: 도구 수십 개, 서버 하나라면 도구 검색의 이득은 작다(토큰은 줄지만 턴이 는다). Claude Code 문서가 말하는 이득은 서버가 여럿이고 도구가 아주 많을 때다. 켜 둔다면 도구 설명과 서버 안내문을 "찾기 쉽게" 써야 한다(과제 1).

## 과제
1. 서버 안내문 · 도구 설명을 고쳐서, 도구 40개 · 도구 검색 켬에서 틀린 질문을 바로잡는다.
2. 클라이언트도 SDK(`ClientSession`)로: 리소스 읽기 · 프롬프트 받기 · 도구 호출을 코드로.
3. 15편 예전 방식 클라이언트(`initialize`)를 SDK 서버에 붙여 본다.
