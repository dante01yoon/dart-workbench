"""20편 공용: 16편 공시 MCP 서버를 세션 하나로 띄워 두고, 스레드에서 동기 함수처럼 부른다.

- 서버: sec16/server_sdk.py (stdio). 연결은 SDK ClientSession, 세션 하나를 계속 쓴다(19편: 호출마다 띄우면 느리다).
- 리서치 팀의 워커는 스레드에서 돈다 → 따로 돌아가는 이벤트 루프에 맡기고 결과를 기다린다(19편 03과 같은 다리).
"""

import asyncio
import json
import sys
import threading
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent


class McpTools:
    WAIT = 60  # 서버가 뜰 때까지 기다리는 초

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.ready = threading.Event()
        self.stop = None
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        fut = asyncio.run_coroutine_threadsafe(self._open(), self.loop)
        if not self.ready.wait(self.WAIT):
            err = fut.exception() if fut.done() else None  # 연결 실패 이유(인증 · 주소)를 같이 알린다
            raise RuntimeError("MCP 서버를 띄우지 못했습니다" + (f": {err!r}"[:240] if err else ""))

    async def _open(self):
        params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "sec16" / "server_sdk.py")])
        self.stop = asyncio.Event()
        async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
            await s.discover()
            self.session = s
            self.tools = [t.name for t in (await s.list_tools()).tools]
            self.ready.set()
            await self.stop.wait()

    def call(self, name, args):
        """도구 결과(JSON 문자열)를 파이썬 값으로. 목록 결과는 항목마다 text 블록 하나."""
        res = asyncio.run_coroutine_threadsafe(self.session.call_tool(name, args), self.loop).result(120)
        vals = [json.loads(c.text) for c in res.content if c.type == "text"]
        return vals[0] if len(vals) == 1 else vals

    def close(self):
        self.loop.call_soon_threadsafe(self.stop.set)
