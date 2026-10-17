"""1편 도구: OpenDART 재무 API로 연결 손익 숫자를 가져온다."""

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

CORP_CODE = {
    "삼성전자": "00126380",
    "SK하이닉스": "00164779",
    "현대자동차": "00164742",
    "카카오": "00258801",
}
ACCOUNTS = {
    "ifrs-full_Revenue": "매출액",
    "dart_OperatingIncomeLoss": "영업이익",
    "ifrs-full_ProfitLoss": "당기순이익",
}


def get_financials(corp: str, year: int) -> dict:
    """사업보고서 연결 손익계산서의 매출액·영업이익·당기순이익(원)."""
    q = urllib.parse.urlencode(
        {
            "crtfc_key": os.environ["DART_API_KEY"],
            "corp_code": CORP_CODE[corp],
            "bsns_year": year,
            "reprt_code": "11011",
            "fs_div": "CFS",
        }
    )
    url = f"https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json?{q}"
    rows = json.load(urllib.request.urlopen(url, timeout=30)).get("list", [])
    out = {}
    for r in rows:
        if r["sj_div"] in ("IS", "CIS") and r["account_id"] in ACCOUNTS:
            out.setdefault(ACCOUNTS[r["account_id"]], int(r["thstrm_amount"]))
    return {"corp": corp, "year": year, "unit": "원", **out}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_financials",
            "description": "한국 상장사의 사업보고서 연결 손익(매출액·영업이익·당기순이익, 원 단위)을 가져온다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "corp": {"type": "string", "enum": list(CORP_CODE)},
                    "year": {"type": "integer", "enum": [2024, 2025]},
                },
                "required": ["corp", "year"],
            },
        },
    }
]
