"""17편: 16편 SDK 서버를 원격(Streamable HTTP)으로 열고, 앞에 Bearer 토큰 인증을 붙인다.

- 도구 · 리소스 · 프롬프트는 16편 것을 그대로 등록한다.
- 이 서버는 '리소스 서버' 역할만 한다: 토큰이 없거나 틀리면 401 + WWW-Authenticate(보호 리소스 메타데이터 주소).
- 토큰 검증: 강의용으로 .env의 MCP_TOKENS("이름;토큰;스코프|스코프;리소스,…")를 쓴다. 서버에는 원문 대신 sha256 해시를 둘 수 있다.
  실서비스는 외부 인가 서버(OAuth)가 발급한 토큰을 검증하도록 verify_token만 바꾼다.
실행: uv run python sec17/server_remote.py  → http://127.0.0.1:8790/mcp
"""

import hashlib
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sec16"))
sys.path.insert(0, str(HERE.parent / "sec15"))
import server as manual  # 15편: 도구 본체 · 회사 목록 · 안내문
import server_sdk as sdk  # 16편: 데코레이터를 붙였던 함수들(그대로 함수다)
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer

HOST = os.environ.get("MCP_HOST", "127.0.0.1")  # Render에서는 0.0.0.0
PORT = int(os.environ.get("PORT") or os.environ.get("MCP_PORT", "8790"))  # Render가 PORT를 준다
PUBLIC = os.environ.get("MCP_PUBLIC_URL", f"http://{HOST}:{PORT}")  # 배포하면 실제 주소
RESOURCE = f"{PUBLIC}/mcp"
SCOPE = "dart:read"


class StaticTokenVerifier:
    """등록된 토큰만 통과. 비교는 sha256 해시로 한다(설정 · 로그가 새도 원문은 안 드러난다). 토큰 값은 출력하지 않는다."""

    def __init__(self, spec):
        self.tokens = {}
        for item in filter(None, (spec or "").split(",")):
            name, token, scopes, resource = item.split(";", 3)  # 스코프 · URL에 콜론이 있어 ;로 나눈다
            key = (
                token
                if token.startswith("sha256:")
                else "sha256:" + hashlib.sha256(token.encode()).hexdigest()
            )
            self.tokens[key] = (name, scopes.split("|"), resource)

    async def verify_token(self, token):
        hit = self.tokens.get("sha256:" + hashlib.sha256(token.encode()).hexdigest())
        if not hit:
            return None
        name, scopes, resource = hit
        return AccessToken(token=token, client_id=name, scopes=scopes, resource=resource)


def toc_reader(corp):
    def read() -> str:
        return sdk.toc(corp)

    return read


def build(wrap=lambda fn: fn):
    """서버를 만든다. wrap: 도구 함수를 감쌀 함수(과제 1에서 호출 기록을 붙일 때 쓴다)."""
    mcp = MCPServer(
        "dart-filings-remote",
        version="0.3.0",
        instructions=manual.INSTRUCTIONS,
        token_verifier=StaticTokenVerifier(os.environ.get("MCP_TOKENS")),
        auth=AuthSettings(
            issuer_url=os.environ.get("MCP_ISSUER_URL", PUBLIC),
            resource_server_url=RESOURCE,
            required_scopes=[SCOPE],  # 이 스코프가 없는 토큰은 403
            validate_token_resource=True,  # 다른 서버용으로 발급된 토큰은 401
        ),
    )
    for fn in (sdk.list_reports, sdk.get_financials, sdk.search_filings):
        mcp.tool(annotations=sdk.READ_ONLY)(wrap(fn))
    for corp in manual.CORPS:
        mcp.resource(
            f"dart://toc/{corp}",
            name=f"{corp} 목차",
            mime_type="text/plain",
            description=f"{corp} 2025 사업보고서 목차(섹션 경로)",
        )(toc_reader(corp))
    mcp.prompt(title="두 회사 비교 리포트")(sdk.compare_companies)
    return mcp


if __name__ == "__main__":
    build().run("streamable-http", host=HOST, port=PORT)
