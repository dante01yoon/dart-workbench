"""과제 2 풀이: 하루 상한을 "횟수" 대신 "실제로 쓴 금액"으로 — 워크벤치가 돈을 쓸 때마다(charge) 오늘 합계에도 더한다.
serve.py 대신 이 파일을 띄우면 된다: DAILY_USD(기본 $0.5)를 넘으면 그날은 새 리서치를 받지 않는다.
사용: uv run uvicorn a2_cost_cap:app --app-dir sec22/solutions --port 8790   ·   모델 없이 시험: uv run python sec22/solutions/a2_cost_cap.py
"""

import datetime
import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path[:0] = [str(ROOT / "sec22"), str(ROOT / "sec20")]
import workbench  # 20편
from fastapi import Request
from fastapi.responses import JSONResponse
from serve import app  # 22편 배포용 서버(접근 코드 · 횟수 상한 포함)

DAILY_USD = float(os.environ.get("DAILY_USD", "0.5"))
today = {"day": "", "usd": 0.0}
lock = threading.Lock()
_charge = workbench.Workbench.charge


def charge(self, cost):  # 리서치 한 번의 상한(20편) + 오늘 합계
    with lock:
        d = datetime.date.today().isoformat()
        if today["day"] != d:
            today.update(day=d, usd=0.0)
        today["usd"] += cost
    _charge(self, cost)


workbench.Workbench.charge = charge


@app.middleware("http")
async def daily_usd(request: Request, call_next):
    spent_today = today["usd"] if today["day"] == datetime.date.today().isoformat() else 0.0
    if request.url.path == "/api/research" and spent_today >= DAILY_USD:
        return JSONResponse(
            {"error": f"오늘 쓴 돈 ${today['usd']:.4f}이 하루 상한 ${DAILY_USD}에 닿았습니다"}, 429
        )
    return await call_next(request)


if __name__ == "__main__":  # 모델을 부르지 않고 합계만 시험
    from fastapi.testclient import TestClient

    DAILY_USD = 0.001
    wb = workbench.Workbench(mcp=None, emit=lambda e: None, cap=1.0)
    for c in (0.0004, 0.0004, 0.0003):
        wb.charge(c)
    c = TestClient(app)
    r = c.get("/api/research", params={"q": "시험"})
    print(f"오늘 합계 ${today['usd']:.4f} / 상한 ${DAILY_USD} → {r.status_code} {r.json()}")
