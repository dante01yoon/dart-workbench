"""과제 2 풀이: 15편 손 구현 서버와 16편 SDK 서버를 한 클라이언트에 같이 붙인다 — 도구 이름이 겹친다.
uv run --no-project --with-requirements sec19/requirements.txt python sec19/solutions/a2_two_servers.py
"""

import asyncio
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from env import DART
from langchain_mcp_adapters.client import MultiServerMCPClient

SERVERS = {"manual": {**DART, "args": ["run", "-q", "python", "sec15/server.py"]}, "sdk": DART}


async def main():
    for prefix in (False, True):
        tools = await MultiServerMCPClient(SERVERS, tool_name_prefix=prefix).get_tools()
        dup = [n for n, c in Counter(t.name for t in tools).items() if c > 1]
        print(f"tool_name_prefix={prefix}: 도구 {len(tools)}개 {[t.name for t in tools]}")
        print(f"  겹친 이름: {dup or '없음'}\n")


asyncio.run(main())
