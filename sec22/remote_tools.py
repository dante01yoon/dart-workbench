"""22편: 워크벤치가 MCP 서버를 로컬 프로세스(stdio) 대신 17편에 배포한 원격 서버(HTTP + 토큰)로 부른다.

- 배포 서버는 검색 색인을 따로 들고 있어서, 워크벤치 서버는 색인 없이 가볍게 뜬다(Render 무료 512MB).
- 배포 서버는 2024 · 2025 두 해라 도구 이름 · 인자가 조금 다르다 → 여기서 맞춰 준다.
  search_filings(query, corp, k) → search_report(query, corp, year=2025, k)
  get_financials(corp)           → get_financials(corp, year=2025), 숫자는 로컬 서버처럼 "8,099,147,815,086" 글자로
- 토큰은 환경 변수 MCP_TOKEN으로만 받는다(값은 출력하지 않는다).
"""

import asyncio
import os
import sys
from pathlib import Path

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec20"))
from mcp_tools import McpTools  # 20편: 세션 하나를 열어 두고 스레드에서 부르는 틀

YEAR = 2025
RENAME = {"search_filings": "search_report"}


class RemoteTools(McpTools):
    WAIT = 150  # 무료 플랜 서버는 잠에서 깨는 데 50초 넘게 걸린다

    async def _open(self):
        url, token = os.environ["MCP_URL"], os.environ["MCP_TOKEN"]
        self.stop = asyncio.Event()
        http = httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=120)
        # 무료 플랜 서버는 쉬면 잠든다 → 토큰 없이 열리는 상태 주소로 먼저 깨운다(깨기 전에 discover를 보내면 시간 초과)
        async with httpx2.AsyncClient(timeout=120) as wake:
            await wake.get(url.rsplit("/mcp", 1)[0] + "/.well-known/oauth-protected-resource/mcp")
        async with http, streamable_http_client(url, http_client=http) as (r, w), ClientSession(r, w) as s:
            await s.discover()
            self.session = s
            self.tools = [t.name for t in (await s.list_tools()).tools]
            self.ready.set()
            await self.stop.wait()

    def call(self, name, args):
        args = {k: v for k, v in args.items() if v is not None}
        if name in ("search_filings", "get_financials"):
            args["year"] = YEAR
        out = super().call(RENAME.get(name, name), args)
        if name == "get_financials" and isinstance(out, dict):
            for v in out.get("accounts", {}).values():
                for k in ("당기", "전기"):
                    if isinstance(v.get(k), int):
                        v[k] = f"{v[k]:,}"
        return out
