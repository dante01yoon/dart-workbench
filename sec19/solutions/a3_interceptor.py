"""과제 3 풀이: 도구 호출을 가로채서(인터셉터) 기록하고, 허용 목록에 없는 도구는 서버까지 보내지 않는다.
18편의 클라이언트 쪽 방어를 어댑터에서 하는 방법이다.
uv run --no-project --with-requirements sec19/requirements.txt python sec19/solutions/a3_interceptor.py
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from env import DART, SYSTEM, llm
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from mcp.types import CallToolResult, TextContent

ALLOW = {"get_financials", "search_filings"}  # list_reports는 일부러 뺐다
LOG = []


async def guard(req, handler):
    t0 = time.time()
    if req.name not in ALLOW:
        LOG.append(f"막음 {req.name}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"{req.name}은 허용되지 않은 도구입니다.")], isError=True
        )
    out = await handler(req)
    LOG.append(f"{req.name}({req.args.get('corp')}) {time.time() - t0:.2f}초")
    return out


async def main():
    tools = await MultiServerMCPClient({"dart": DART}, tool_interceptors=[guard]).get_tools()
    agent = create_agent(llm(), tools, system_prompt=SYSTEM)
    q = "검색할 수 있는 보고서 목록을 먼저 확인하고, SK하이닉스 2025년 영업이익을 알려줘."
    out = await agent.ainvoke({"messages": [("user", q)]})
    print("호출 기록:", " · ".join(LOG))
    print(out["messages"][-1].content[:400])


asyncio.run(main())
