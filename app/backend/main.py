"""캡스톤 백엔드 — FastAPI + SSE (강의 20편).
GET /api/research?q=...  → text/event-stream: planning → plan → task_start/task_end … → writing → done
GET /api/reports          → 수집된 보고서 목록
실행: .venv/bin/uvicorn app.backend.main:app --port 8787
"""

import asyncio
import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402

from dart_rag.team import Team  # noqa: E402
from mcp_server.manual import call_tool  # noqa: E402

app = FastAPI(title="AI 투자 리서치 워크벤치")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["GET"], allow_headers=["*"])
_team = None
_lock = threading.Lock()  # 비용 상한: 동시에 하나의 리서치만


def team():
    global _team
    if _team is None:
        _team = Team()
    return _team


@app.get("/api/reports")
def reports():
    return call_tool("list_reports", {})


@app.get("/api/financials")
def financials():
    """4개사 × 2개년 연결 손익(재무 API). 프론트의 재무 차트용."""
    out = []
    for r in call_tool("list_reports", {}):
        d = call_tool("get_financials", {"corp": r["corp"], "year": r["year"]})
        out.append({"corp": r["corp"], "year": r["year"], **{k: v["당기"] for k, v in d["accounts"].items()}})
    return out


@app.get("/api/scorecard")
def scorecard():
    """하네스 성적표(답변 전체) + 검색 성적표(recall@5·MRR)."""
    root = Path(__file__).resolve().parents[2]
    runs = []
    p = root / "data" / "scorecard.jsonl"
    if p.exists():
        runs = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    retrieval = []
    for f in sorted((root / "eval").glob("scorecard*.json")):
        tags = f.stem.replace("scorecard", "").strip("-").split("-") if f.stem != "scorecard" else []
        for method, v in json.loads(f.read_text()).items():
            retrieval.append({"method": method, "filter": "filter" in tags, "para": "para" in tags, "ctx": "ctx" in tags,
                              "recall5": v["recall@5"], "mrr10": v["mrr@10"], "n": v["n"]})
    return {"runs": runs, "retrieval": retrieval}


@app.get("/api/research")
async def research(q: str = Query(..., min_length=2, max_length=300)):
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def emit(e):
        loop.call_soon_threadsafe(queue.put_nowait, e)

    def work():
        if not _lock.acquire(blocking=False):
            emit({"type": "error", "message": "다른 리서치가 진행 중입니다. 잠시 뒤 다시 시도하세요."})
            return
        try:
            team().run(q, emit=emit)
        except Exception as ex:  # noqa: BLE001
            emit({"type": "error", "message": str(ex)[:300]})
        finally:
            _lock.release()

    threading.Thread(target=work, daemon=True).start()

    async def stream():
        while True:
            e = await queue.get()
            yield f"data: {json.dumps(e, ensure_ascii=False)}\n\n"
            if e["type"] in ("done", "error"):
                break

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
