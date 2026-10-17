"""21편: 20편 서버에 화면이 쓸 API 두 개를 더한다(20편 server.py는 그대로 둔다).

GET /api/companies         → 회사 목록 + 사업보고서 접수번호 + DART 원문 주소
GET /api/financials?corp=  → MCP 재무 도구(get_financials)의 숫자를 차트용으로
실행: uv run uvicorn api:app --app-dir sec21 --port 8790   (화면은 sec21/web에서 npm run dev)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sec20"))
from fastapi import HTTPException
from server import app, tools  # 20편 앱(/api/research SSE)을 그대로 가져온다

DART_VIEWER = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo="


@app.get("/api/companies")
def companies():
    out = []
    for f in sorted((ROOT / "data" / "reports").glob("*_2025.json")):
        r = json.loads(f.read_text())
        out.append(
            {
                "corp": r["corp"],
                "year": r["year"],
                "rcept_no": r["rcept_no"],
                "url": DART_VIEWER + r["rcept_no"],
            }
        )
    return out


@app.get("/api/financials")
def financials(corp: str):
    fin = tools().call("get_financials", {"corp": corp})
    if not isinstance(fin, dict) or "accounts" not in fin:
        raise HTTPException(404, f"재무 숫자가 없습니다: {corp}")
    return [
        {
            "account": acc,
            "current": int(v["당기"].replace(",", "")),
            "previous": int(v["전기"].replace(",", "")),
        }
        for acc, v in fin["accounts"].items()
    ]
