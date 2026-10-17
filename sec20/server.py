"""20편: 워크벤치 백엔드 — FastAPI + SSE.

GET /api/research?q=...  → text/event-stream으로 진행 이벤트를 하나씩 보낸다(planning → plan → task … → done)
GET /                    → 이벤트를 받아 그리는 확인용 화면(21편에서 React로 다시 만든다)
- 리서치는 동시에 하나만(비용 보호). 한 번에 쓸 수 있는 돈은 COST_CAP(기본 $0.05).
실행: uv run uvicorn server:app --app-dir sec20 --port 8790
"""

import asyncio
import json
import os
import threading
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, StreamingResponse
from mcp_tools import McpTools
from workbench import BudgetExceeded, Workbench

HERE = Path(__file__).resolve().parent
CAP = float(os.environ.get("COST_CAP", "0.05"))
app = FastAPI(title="AI 투자 리서치 워크벤치")
lock = threading.Lock()  # 동시에 하나의 리서치만
mcp = None


def tools():
    global mcp
    if mcp is None:
        mcp = McpTools()  # 첫 요청 때 MCP 서버를 띄우고 계속 쓴다
    return mcp


@app.get("/")
def page():
    return FileResponse(HERE / "live.html")


@app.get("/api/research")
async def research(q: str = Query(..., min_length=2, max_length=300), cap: float = CAP):
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def emit(e):
        loop.call_soon_threadsafe(queue.put_nowait, e)

    def work():
        if not lock.acquire(blocking=False):
            emit({"type": "error", "message": "다른 리서치가 진행 중입니다. 잠시 뒤 다시 시도하세요."})
            emit(None)
            return
        wb = None
        try:
            wb = Workbench(tools(), emit, cap=min(cap, CAP))
            wb.research(q)
        except BudgetExceeded as e:
            emit(
                {
                    "type": "budget",
                    "message": f"비용 상한에 걸려 멈췄습니다: {e}",
                    "spent": round(wb.spent, 4),
                }
            )
        except Exception as e:  # noqa: BLE001 — 실패도 이벤트로 알린다
            emit({"type": "error", "message": str(e)[:200]})
        finally:
            lock.release()
            emit(None)

    threading.Thread(target=work, daemon=True).start()

    async def stream():
        while (e := await queue.get()) is not None:
            yield f"event: {e['type']}\ndata: {json.dumps(e, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
