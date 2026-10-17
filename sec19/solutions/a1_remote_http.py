"""과제 1 풀이: 어댑터로 17편 원격 서버(HTTP + 토큰)에 붙는다. 토큰은 헤더로만 넘기고 출력하지 않는다.
uv run --no-project --with-requirements sec19/requirements.txt python sec19/solutions/a1_remote_http.py [주소]
"""

import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from env import SYSTEM, llm
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

URL = sys.argv[1] if len(sys.argv) > 1 else "https://dart-mcp-324k.onrender.com/mcp"
TOKEN = os.environ["MCP_TOKEN_GOOD" if URL.startswith("http://127.0.0.1") else "MCP_TOKEN_REMOTE"]


async def main():
    client = MultiServerMCPClient(
        {
            "dart": {
                "transport": "streamable_http",
                "url": URL,
                "headers": {"Authorization": f"Bearer {TOKEN}"},
            }
        }
    )
    t0 = time.time()
    tools = await client.get_tools()
    print(f"도구 {[t.name for t in tools]} ({time.time() - t0:.1f}초)")
    agent = create_agent(llm(), tools, system_prompt=SYSTEM.replace("search_filings", "검색 도구"))
    t0 = time.time()
    out = await agent.ainvoke({"messages": [("user", "현대자동차 2025년 매출과 최대주주를 알려줘.")]})
    calls = [tc["name"] for m in out["messages"] for tc in (getattr(m, "tool_calls", None) or [])]
    print(f"도구 호출 {calls}, {time.time() - t0:.1f}초\n{out['messages'][-1].content[:500]}")


asyncio.run(main())
