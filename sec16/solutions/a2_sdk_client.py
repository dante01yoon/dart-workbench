"""과제 2 풀이: 클라이언트도 SDK로 — 15편 01_talk처럼 손으로 JSON을 쓰지 않고 ClientSession으로 서버를 쓴다.
도구 목록 · 리소스 읽기 · 프롬프트 받기 · 도구 호출을 한 번씩. 15편 서버(dual-era)에도 그대로 붙는지 본다.
사용: uv run python sec16/solutions/a2_sdk_client.py [서버 파일]
"""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent.parent


async def main(target):
    params = StdioServerParameters(command=sys.executable, args=[str(target)])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.discover()  # 2026-07-28 방식(server/discover). s.initialize()는 예전 핸드셰이크다
        print("서버:", s.server_info.name if s.server_info else "?", "· 버전:", s.protocol_version)
        tools = await s.list_tools()
        print("도구:", [t.name for t in tools.tools])
        caps = s.server_capabilities
        if caps and caps.resources:
            res = await s.list_resources()
            print("리소스:", [x.name for x in res.resources])
            toc = await s.read_resource(res.resources[2].uri)
            print("  ", res.resources[2].name, "→", toc.contents[0].text.splitlines()[:3], "…")
        if caps and caps.prompts:
            p = await s.get_prompt("compare_companies", {"corp_a": "삼성전자", "corp_b": "SK하이닉스"})
            print("프롬프트:", p.messages[0].content.text.splitlines()[0])
        r = await s.call_tool("get_financials", {"corp": "SK하이닉스"})
        print("도구 호출:", r.content[0].text[:120].replace("\n", " "), "…")


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "sec16" / "server_sdk.py"))
