# 15편 과제 풀이 (실측 2026-10-13)

## 과제 1 — 도구 하나 더 (`solutions/a1_company_info.py`, `solutions/mcp_a1.json`)
- 서버 코드는 그대로 두고 `TOOLS`에 하나를 더하고 `call_tool`만 감쌌다(2편 `company_info` API 그대로).
- `claude -p "카카오 대표이사가 누구야?" --strict-mcp-config --mcp-config sec15/solutions/mcp_a1.json --model haiku --tools "" --allowedTools "mcp__dart__*"` → "카카오의 대표이사는 정신아" + 설립일 · 본사 주소. 서버 기록: discover 1 · tools/list 1(도구 4개) · tools/call `company_info {"corp": "카카오"}` 1. 2턴, $0.0004.
- 주의: `-p`(비대화) 모드에서는 MCP 도구에도 허락이 필요하다. `--allowedTools "mcp__dart__*"` 없이 돌리면 "권한이 거부됐다"며 기억으로 답했다($0.0019).

## 과제 2 — 예전 클라이언트 (`solutions/a2_legacy_client.py`)
- `initialize`(protocolVersion 2025-11-25) → 서버가 같은 버전으로 답하고, 그 연결은 예전 방식이 된다 → `_meta` 없이 `tools/list` · `tools/call`이 통한다(카카오 재무 숫자).
- 우리 서버는 예전 방식 연결에도 새 방식 결과 틀(`resultType` · `_meta`)을 그대로 붙여 보냈다. 예전 클라이언트는 모르는 필드를 무시해서 문제는 없었지만, SDK 서버는 시대별로 다르게 답한다(16편 과제 3).

## 과제 3 — 오류 결과 (`solutions/a3_validate.py`)
- `get_financials(corp="LG전자")`를 직접 보내면: 원래 서버는 `isError: false`에 `accounts: {}`(빈 결과가 성공처럼 보인다), 고친 서버는 `isError: true` "corp='LG전자'는 지원하지 않습니다. 가능한 값: 삼성전자, SK하이닉스, 현대자동차, 카카오".
- Claude Code에 "LG전자 영업이익 알려줘"를 물으면 두 서버 모두 도구를 아예 부르지 않았다. 입력 스키마의 `enum`을 보고 모델이 먼저 "지원 목록에 없다"고 답했다 → 스키마가 첫 번째 방어선, `isError`는 스키마를 거치지 않는 호출(다른 클라이언트 · 직접 호출)을 위한 두 번째 방어선이다.
