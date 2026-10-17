"""19편 01: 내 MCP 서버(16편 SDK 서버)를 LangChain MCP 어댑터로 불러와 LangGraph 에이전트에 붙인다.

uv run --no-project --with-requirements sec19/requirements.txt python sec19/01_adapter.py
"""

import asyncio
import sys
import time

from env import DART, MODEL, SYSTEM, llm
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient


def text(content):  # 도구 결과는 문자열이거나 [{"type": "text", "text": …}] 목록
    return content if isinstance(content, str) else "".join(c.get("text", "") for c in content)


Q = " ".join(sys.argv[1:]) or "카카오 2025년 영업이익과 최대주주를 알려줘. 출처도."


async def main():
    client = MultiServerMCPClient({"dart": DART})
    t0 = time.time()
    tools = await client.get_tools()  # MCP 도구 → LangChain 도구(이름 · 설명 · 입력 형식 그대로)
    print(f"■ MCP 도구 {len(tools)}개 → LangChain 도구 ({time.time() - t0:.1f}초)")
    for t in tools:
        print(f"  {t.name}({', '.join(t.args)}) — {t.description[:44]}…")

    agent = create_agent(llm(), tools, system_prompt=SYSTEM)  # 결과는 LangGraph 그래프
    print("\n■ 에이전트 그래프:", " → ".join(n for n in agent.get_graph().nodes if not n.startswith("__")))
    print(f"■ 질문: {Q}  (모델 {MODEL})\n")
    t0 = time.time()
    async for step in agent.astream({"messages": [("user", Q)]}, stream_mode="updates"):
        for node, upd in step.items():
            for m in upd.get("messages", []):
                for tc in getattr(m, "tool_calls", None) or []:
                    print(f"  {time.time() - t0:5.1f}초  {node}: {tc['name']}({tc['args']})")
                if node == "tools":
                    print(f"  {time.time() - t0:5.1f}초  tools: {m.name} → {len(text(m.content)):,}자 받음")
                elif not getattr(m, "tool_calls", None):
                    answer = m.content
    print(f"\n■ 답 ({time.time() - t0:.1f}초)\n{answer}")


asyncio.run(main())
