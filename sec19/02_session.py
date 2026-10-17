"""19편 02: 어댑터 기본값은 도구를 부를 때마다 서버를 새로 띄운다 → 세션을 열어 두면 얼마나 빨라지나.

uv run --no-project --with-requirements sec19/requirements.txt python sec19/02_session.py
"""

import asyncio
import time

from env import DART
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

CALLS = [
    ("list_reports", {}),
    ("search_filings", {"query": "최대주주", "corp": "카카오", "k": 3}),
    ("list_reports", {}),
]


async def run(tools, label):
    by = {t.name: t for t in tools}
    times = []
    for name, args in CALLS:
        t0 = time.time()
        await by[name].ainvoke(args)
        times.append(time.time() - t0)
    print(
        f"  {label:<22} "
        + " · ".join(f"{n} {s:.2f}초" for (n, _), s in zip(CALLS, times))
        + f"  = {sum(times):.1f}초"
    )


async def main():
    client = MultiServerMCPClient({"dart": DART})
    print("■ 같은 도구 세 번 부르기\n")
    await run(await client.get_tools(), "기본(호출마다 새 서버)")
    async with client.session("dart") as s:  # 서버 하나를 띄워 두고 계속 쓴다
        await run(await load_mcp_tools(s), "세션 유지")


asyncio.run(main())
