# 17편 과제 풀이 (실측 2026-10-13)

## 과제 1 — 호출 기록 (`solutions/a1_audit_log.py`)
- `server_remote.build(wrap=audited)`: 도구 함수를 `functools.wraps`로 감싸 이름 · 타입 힌트 · 설명을 그대로 두고(SDK가 같은 입력 형식을 만든다), 부를 때마다 `get_access_token()`의 `client_id` · 스코프 · 도구 · 인자를 `data/mcp_audit.jsonl`에 쓴다.
- 01_auth_test를 돌린 뒤 로그: `dante` 이름으로 get_financials · list_reports만 남았다. 401 · 403으로 거절된 요청(스코프 부족 · 다른 서버용 토큰)은 **도구까지 오지 않아서** 기록되지 않는다 → 거절 기록이 필요하면 HTTP 앞단(로그 · 미들웨어)에서 남긴다.

## 과제 2 — SDK HTTP 클라이언트 (`solutions/a2_http_client.py`)
- `httpx2.AsyncClient(headers={"Authorization": "Bearer …"})`를 `streamable_http_client(URL, http_client=…)`에 넘긴다. `Mcp-Method` · `Mcp-Name` 헤더는 SDK가 붙인다.
- 내 컴퓨터: discover 0.00초, 도구 3개, get_financials(카카오) 2.62초(재무 API 호출 포함).
- 배포 서버: discover 0.19초, 도구 `list_reports · get_financials · search_report`, get_financials 0.40초(배포판은 재무 값을 미리 받아 둠).

## 과제 3 — 토큰 만들기 (`solutions/a3_make_token.py`)
- `secrets.token_urlsafe(32)`(256비트) → `.env`에 `MCP_TOKEN_<이름>`으로 추가, 화면에는 서버에 넣을 줄 `이름;sha256:<해시>;dart:read;<주소>`만 찍는다.
- 확인: `MCP_TOKENS`에 해시만 넣고 서버를 띄워도 원래 토큰이 200으로 통과했다(서버는 받은 토큰을 해시해서 비교한다).
