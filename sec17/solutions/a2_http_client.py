"""과제 2 풀이: SDK 클라이언트로 원격 서버에 붙는다 — 토큰은 HTTP 클라이언트의 기본 헤더로 넣는다(값은 출력하지 않는다).
Mcp-Method · Mcp-Name 헤더와 세션은 SDK가 알아서 붙인다(01_auth_test.py에서 손으로 넣던 것).
사용: uv run python sec17/solutions/a2_http_client.py [주소]   (기본: 내 컴퓨터 8790)
"""

import asyncio
import os
import sys
import time
from pathlib import Path

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "sec02"))
import tools15  # noqa: F401  (.env)

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8790/mcp"
REMOTE = not URL.startswith("http://127.0.0.1")
TOKEN = os.environ["MCP_TOKEN_REMOTE" if REMOTE else "MCP_TOKEN_GOOD"]


async def main():
    http = httpx2.AsyncClient(headers={"Authorization": f"Bearer {TOKEN}"}, timeout=120)
    async with http, streamable_http_client(URL, http_client=http) as (r, w), ClientSession(r, w) as s:
        t0 = time.time()
        await s.discover()
        print(f"discover {time.time() - t0:.2f}초 · 서버 {s.server_info.name} · 버전 {s.protocol_version}")
        print("도구:", [t.name for t in (await s.list_tools()).tools])
        args = {"corp": "카카오", "year": 2025} if REMOTE else {"corp": "카카오"}
        t0 = time.time()
        res = await s.call_tool("get_financials", args)
        print(f"get_financials {time.time() - t0:.2f}초:", res.content[0].text[:110].replace("\n", " "), "…")


asyncio.run(main())
