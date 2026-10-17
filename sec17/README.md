# 17편 원격 MCP — Streamable HTTP + Bearer 인증 + Render 배포

## 파일
| 파일 | 내용 |
|---|---|
| `server_remote.py` | 16편 SDK 서버의 도구 · 리소스 · 프롬프트를 그대로 등록하고, Streamable HTTP로 연다(`http://127.0.0.1:8790/mcp`). 앞에 Bearer 토큰 인증(리소스 서버 역할): `AuthSettings(required_scopes=["dart:read"], validate_token_resource=True)` + `StaticTokenVerifier`(토큰을 sha256 해시로 비교) |
| `01_auth_test.py` | 틀린 토큰 5종 · 맞는 토큰 1종 → HTTP 상태 확인, 401이 알려 주는 보호 리소스 메타데이터, `Mcp-Method` 헤더를 뺀 요청, 왕복 시간. 주소를 주면 배포 서버를 시험한다. 토큰 값은 출력하지 않는다 |
| `mcp_local.json` · `mcp_remote.json` | Claude Code 설정(HTTP). 토큰은 `${MCP_TOKEN_GOOD}` · `${MCP_TOKEN_REMOTE}` 환경 변수로만 넣는다 |
| `render.yaml` | Render 무료 웹 서비스 설정. 키 · 토큰 해시는 대시보드에서 직접 넣는다(`sync: false`) |

## 실행
```bash
uv run python sec17/server_remote.py > data/server17.log 2>&1 &
uv run python sec17/01_auth_test.py
uv run python sec17/01_auth_test.py https://<내 주소>/mcp
# Claude Code: 토큰 값을 화면에 찍지 않고 환경 변수로만 넘긴다
export MCP_TOKEN_REMOTE="$(grep '^MCP_TOKEN_REMOTE=' .env | cut -d= -f2-)"
claude --strict-mcp-config --mcp-config sec17/mcp_remote.json --model haiku --tools ""
```
- `.env`에 필요한 이름: `MCP_TOKENS`(서버가 받는 토큰 목록 `이름;토큰;스코프|스코프;리소스,…`), `MCP_TOKEN_GOOD` · `MCP_TOKEN_NOSCOPE` · `MCP_TOKEN_OTHER`(시험용), `MCP_TOKEN_REMOTE`(배포 서버용). 새 토큰은 과제 3 풀이로 만든다.
- 주의: `source .env`로 불러오지 말 것. `MCP_TOKENS` 줄의 `;` 때문에 셸이 토큰 조각을 명령으로 실행하려다 오류 메시지에 값을 찍는다(녹화 전 실제로 겪었다).
- Render: 공시 본문(`data/rag`)은 공개 금지라 **비공개 저장소**에 `git add -f data/rag data/reports`로 넣고, `render.yaml`을 저장소 맨 위에 두어 Blueprint로 만든다. 무료 플랜 512MB — 이 서버는 검색까지 한 뒤 약 317MB였다. 쉬면 잠들어서 첫 요청이 40~50초 걸린다.

## 개념 출처
- MCP 규격 2026-07-28 Authorization: MCP 서버는 OAuth 2.1 **리소스 서버**, 보호 리소스 메타데이터(RFC 9728) 필수, 토큰은 매 요청 `Authorization: Bearer` 헤더(쿼리 문자열 금지), 자기에게 발급된 토큰만 받는다(RFC 8707 audience), 401 = 토큰 없음 · 틀림, 403 = 스코프 부족.
- MCP 보안 모범 사례: "Token Passthrough" 금지, "Scope Minimization"(처음엔 최소 스코프).
- 2026-07-28 Streamable HTTP: 본문의 method · 도구 이름을 `Mcp-Method` · `Mcp-Name` 헤더에도 적는다(빠지면 400, -32020 — mcp 2.3.0 실측).

## 실제 결과 (2026-10-13 녹화 전 실측, mcp 2.3.0)
- 내 컴퓨터: 6/6 기대대로 — 토큰 없음 · 틀린 토큰 · "Bearer " 없이 토큰만 · 다른 서버용 토큰 → 401, 스코프 부족 → 403(`insufficient_scope`), 올바른 토큰 → 200. 401 헤더의 `resource_metadata` → `{"resource": ".../mcp", "scopes_supported": ["dart:read"]}`. `Mcp-Method` 헤더를 빼면 400 -32020. `list_reports` 왕복 중앙값 13ms.
- 배포 서버(https://dart-mcp-324k.onrender.com/mcp, 참조 구현을 같은 방식으로 올린 것 — 2024 · 2025 두 해라 `get_financials`에 `year`가 있고 검색 도구 이름이 `search_report`): 잠든 상태에서 첫 요청 42초, 4/4 기대대로, `list_reports` 왕복 중앙값 236ms.
- Claude Code(Haiku) → 배포 서버: "카카오 2025년 영업이익과 최대주주" → get_financials + search_report, 11.5초, $0.0011. 영업이익 7,320억 원(전기 4,953억), 최대주주 김범수 13.28%(「VII. 주주에 관한 사항」).

## 과제
1. 누가 어떤 도구를 불렀는지 기록한다(토큰 이름 = client_id). 토큰 값은 남기지 않는다.
2. 클라이언트도 SDK로: `streamable_http_client` + 토큰 헤더로 원격 서버의 도구를 부른다.
3. 내 토큰을 하나 만든다: 원문은 `.env`에만, 서버에는 sha256 해시만.
