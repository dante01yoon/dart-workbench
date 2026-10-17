"""내 MCP 서버를 LangChain 어댑터로 LangGraph 에이전트에 붙이기 (강의 19편).

주의: langchain-mcp-adapters 0.3.2는 mcp<2를 요구한다 → 서버(mcp 2.3.0)와 다른 가상환경(.venv-adapters)에서 실행한다.
클라이언트(mcp 1.30)는 예전 방식(initialize)으로 말하고, 15편 손 구현 서버는 dual-era라 그대로 받는다.
사용: .venv-adapters/bin/python frameworks/lc_mcp_agent.py "질문"
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

ROOT = Path(__file__).resolve().parent.parent
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


async def main(q):
    client = MultiServerMCPClient({"dart": {
        "transport": "stdio",
        "command": str(ROOT / ".venv" / "bin" / "python"),  # 서버는 mcp 2.3 환경에서
        "args": ["-W", "ignore", str(ROOT / "mcp_server" / "manual.py")],
    }})
    tools = await client.get_tools()
    print("MCP 도구:", [t.name for t in tools], flush=True)
    llm = ChatOpenAI(model=os.environ["FAST_MODEL"], base_url=os.environ["OPENAI_BASE_URL"], api_key=os.environ["OPENAI_API_KEY"],
                     extra_body={"reasoning": {"effort": "none"}})
    agent = create_react_agent(llm, tools, prompt="한국 상장사 사업보고서 도우미. 숫자는 get_financials, 서술은 search_report. 출처(섹션)를 적고 투자 권유는 하지 마라.")
    t0 = time.time()
    out = await agent.ainvoke({"messages": [("user", q)]})
    for m in out["messages"]:
        for tc in getattr(m, "tool_calls", []) or []:
            print("  도구 호출:", tc["name"], tc["args"], flush=True)
    print(f"\n{time.time() - t0:.1f}s\n", out["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:]) or "카카오 2025년 영업이익과 최대주주를 알려줘"))
