"""22편: 배포용 서버 하나 — 21편 API + 빌드한 React 화면 + 접근 코드 + 하루 리서치 횟수 상한.

- 화면: sec21/web을 `npm run build` 한 dist/를 같은 서버가 내준다(서버 하나, 주소 하나).
- MCP: MCP_URL이 있으면 17편 배포 서버(remote_tools.RemoteTools), 없으면 20편처럼 로컬 프로세스.
- 접근 코드: 처음 한 번 /?code=… 로 들어오면 쿠키를 심고, /api/research는 쿠키가 맞아야 돈다(EventSource는 헤더를 못 붙여서 쿠키).
- 하루 상한: 리서치는 하루 DAILY_RUNS번까지(기본 30). 한 번의 상한 COST_CAP($0.05)과 곱하면 하루 최대 $1.5.
실행: uv run uvicorn serve:app --app-dir sec22 --port 8790
"""

import datetime
import hmac
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sec21"))
sys.path.insert(0, str(ROOT / "sec20"))
import server  # 20편 서버(전역 mcp · 잠금)
from api import app  # 21편: 20편 앱 + /api/companies · /api/financials
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

CODE = os.environ.get("ACCESS_CODE", "")
DAILY_RUNS = int(os.environ.get("DAILY_RUNS", "30"))
DIST = ROOT / "sec21" / "web" / "dist"
runs = {"day": "", "n": 0}

if os.environ.get("MCP_URL"):
    import api
    from remote_tools import RemoteTools

    def remote():  # 첫 요청 때 연결한다 — 원격 서버가 잠들어 있어도 이 서버는 바로 뜬다
        if server.mcp is None:
            server.mcp = RemoteTools()
        return server.mcp

    server.tools = api.tools = remote  # 20편 리서치 · 21편 재무 API가 이걸 부른다

app.router.routes = [
    r for r in app.router.routes if getattr(r, "path", "") != "/"
]  # 20편 확인용 화면 대신 React 화면


@app.middleware("http")
async def guard(request: Request, call_next):
    given = request.query_params.get("code")
    if request.url.path == "/" and CODE and given is not None:
        res = RedirectResponse("/")  # 주소창에서 코드를 지운다
        if hmac.compare_digest(given, CODE):
            res.set_cookie("code", given, httponly=True, samesite="strict", max_age=7 * 86400)
        return res
    if request.url.path == "/api/research":
        if CODE and not hmac.compare_digest(request.cookies.get("code", ""), CODE):
            return JSONResponse({"error": "접근 코드가 필요합니다"}, status_code=401)
        today = datetime.date.today().isoformat()
        if runs["day"] != today:
            runs.update(day=today, n=0)
        if runs["n"] >= DAILY_RUNS:
            return JSONResponse({"error": f"오늘 리서치 {DAILY_RUNS}번을 다 썼습니다"}, status_code=429)
        runs["n"] += 1
    return await call_next(request)


@app.get("/healthz")
def healthz():
    return {"ok": True, "runs_today": runs["n"], "daily_runs": DAILY_RUNS}


if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
