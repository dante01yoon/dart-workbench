"""원격 MCP 서버: Streamable HTTP + Bearer 토큰 인증 (강의 17편).

- 16편 SDK 서버의 도구·리소스·프롬프트를 그대로 등록하고, 앞에 인증을 붙인다.
- 리소스 서버 역할만 한다: 토큰이 없거나 틀리면 401 + WWW-Authenticate(protected resource metadata 주소).
- 토큰 검증: 강의용으로 .env의 MCP_TOKENS("이름;토큰;스코프|스코프;리소스,…")를 쓴다. 실서비스는 외부 인가 서버(OAuth)의 토큰을 검증한다.
- validate_token_resource=True: 다른 서버용으로 발급된 토큰(aud/resource 불일치)은 거절한다.
실행: .venv/bin/python mcp_server/remote.py  → http://127.0.0.1:8790/mcp
"""

import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.auth.provider import AccessToken  # noqa: E402
from mcp.server.auth.settings import AuthSettings  # noqa: E402
from mcp.server.mcpserver import MCPServer  # noqa: E402

from mcp_server import manual, sdk  # noqa: E402

HOST = os.environ.get("MCP_HOST", "127.0.0.1")  # Render에서는 0.0.0.0
PORT = int(os.environ.get("PORT") or os.environ.get("MCP_PORT", "8790"))  # Render가 PORT를 준다
PUBLIC = os.environ.get("MCP_PUBLIC_URL", f"http://{HOST}:{PORT}")  # 배포하면 Render 주소
RESOURCE = f"{PUBLIC}/mcp"
SCOPE = "dart:read"


class StaticTokenVerifier:
    """MCP_TOKENS에 등록된 토큰만 통과시킨다. 토큰 값은 로그에 남기지 않는다.
    서버에는 토큰 원문 대신 "sha256:<해시>"를 저장할 수 있다 — 설정·로그가 새도 토큰은 드러나지 않는다(배포판은 해시만)."""

    def __init__(self, spec):
        self.tokens = {}
        for item in filter(None, (spec or "").split(",")):
            name, token, scopes, resource = item.split(";", 3)  # 스코프(dart:read)·URL에 콜론이 있어 ;로 나눈다
            key = token if token.startswith("sha256:") else "sha256:" + hashlib.sha256(token.encode()).hexdigest()
            self.tokens[key] = (name, scopes.split("|"), resource)

    async def verify_token(self, token):
        hit = self.tokens.get("sha256:" + hashlib.sha256(token.encode()).hexdigest())
        if not hit:
            return None
        name, scopes, resource = hit
        return AccessToken(token=token, client_id=name, scopes=scopes, resource=resource)


server = MCPServer(
    "dart-filings-remote", version="0.3.0", instructions=manual.INSTRUCTIONS,
    token_verifier=StaticTokenVerifier(os.environ.get("MCP_TOKENS")),
    auth=AuthSettings(issuer_url=os.environ.get("MCP_ISSUER_URL", PUBLIC), resource_server_url=RESOURCE,
                      required_scopes=[SCOPE], validate_token_resource=True),
)
for fn in (sdk.list_reports, sdk.get_financials, sdk.search_report):
    server.tool(annotations=sdk.READ_ONLY)(fn)
server.resource("dart://reports", mime_type="application/json", description="수집된 사업보고서 목록")(sdk.reports)
server.resource("dart://toc/{corp}/{year}", mime_type="text/plain", description="한 보고서의 목차(섹션 경로)")(sdk.toc)
server.prompt(title="두 회사 비교 리포트")(sdk.compare_companies)

if __name__ == "__main__":
    server.run("streamable-http", host=HOST, port=PORT)
