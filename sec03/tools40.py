"""3편 도구 40개 = 2편 도구 15개 + 실제 도구 3개 + 그럴듯한 미끼 22개.

미끼는 이름과 설명만 있고 이 강의 환경에는 연결돼 있지 않다(부르면 "연결되지 않음" 오류).
실제 서비스에서도 도구가 늘면 비슷한 이름, 겹치는 설명, 쓰지 않는 도구가 함께 늘어난다.
"""

import sys
from pathlib import Path

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec02"))
import tools15
from tools15 import ROOT, CorpYear, _tool

EXTRA_REAL = [
    (
        "capital_changes",
        "irdsSttus.json",
        CorpYear,
        "증자·감자 현황: 주식 발행(유상·무상증자, 주식매수선택권 행사)·감자 날짜·형태·수량. 자기주식은 treasury_stock.",
        "증자",
        ["isu_dcrs_de", "isu_dcrs_stle", "isu_dcrs_stock_knd", "isu_dcrs_qy"],
    ),
    (
        "share_count",
        "stockTotqySttus.json",
        CorpYear,
        "주식의 총수: 발행할 주식 총수, 발행 주식 총수, 자기주식 수, 유통 주식 수(기말).",
        "주식 수",
        ["se", "isu_stock_totqy", "istc_totqy", "tesstk_co", "distb_stock_co"],
    ),
    (
        "other_corp_investments",
        "otrCprInvstmntSttus.json",
        CorpYear,
        "타법인 출자 현황: 다른 회사에 투자한 지분율과 장부가액(기말).",
        "출자",
        ["inv_prm", "invstmnt_purps", "trmend_blce_qota_rt", "trmend_blce_acntbk_amount"],
    ),
]


class Query(BaseModel):
    query: str


DECOYS = [
    ("stock_price_history", "일별 주가(시가·종가·거래량) 조회.", CorpYear),
    ("analyst_target_price", "증권사 애널리스트 목표 주가와 투자의견.", CorpYear),
    ("esg_score", "ESG 평가 등급.", CorpYear),
    ("news_sentiment", "뉴스 감성 점수.", CorpYear),
    ("patent_search", "특허 검색.", Query),
    ("real_estate_price", "아파트 실거래가.", Query),
    ("exchange_rate", "원/달러 환율.", Query),
    ("commodity_price", "원자재 가격(유가·구리).", Query),
    ("dividend_forecast", "내년 예상 배당금 추정치(증권사 컨센서스).", CorpYear),
    ("shareholder_meeting_minutes", "주주총회 회의록 원문.", CorpYear),
    ("executive_bio_web", "웹에서 임원 프로필 검색.", Query),
    ("employee_reviews", "직원 회사 리뷰(평점).", CorpYear),
    ("competitor_list", "경쟁사 목록 추천.", CorpYear),
    ("industry_report", "산업 리포트 요약.", Query),
    ("macro_indicator", "GDP·금리 같은 거시 지표.", Query),
    ("bond_yield", "국고채 금리.", Query),
    ("ipo_calendar", "공모주 일정.", Query),
    ("insider_trading_us", "미국 SEC 내부자 거래(Form 4).", Query),
    ("credit_rating", "신용등급(회사채).", CorpYear),
    ("short_interest", "공매도 잔고.", CorpYear),
    ("foreign_ownership", "외국인 보유 비율(일별).", CorpYear),
    ("earnings_call_transcript", "실적 발표 콘퍼런스콜 녹취.", CorpYear),
]

for spec in EXTRA_REAL:
    tools15.SPEC.append(spec)
    tools15._BY_NAME[spec[0]] = spec

TOOLS15 = tools15.TOOLS
TOOLS3 = [t for t in TOOLS15 if t["function"]["name"] in ("company_info", "key_accounts", "dividends")]
TOOLS40 = (
    TOOLS15
    + [_tool(n, m, good) for n, _, m, good, _, _ in EXTRA_REAL]
    + [_tool(n, m, d) for n, d, m in DECOYS]
)
_DECOY_NAMES = {n for n, _, _ in DECOYS}


def run_tool(name: str, args: dict) -> dict:
    if name in _DECOY_NAMES:
        return {"error": f"'{name}'은(는) 이 환경에 연결되지 않은 도구입니다. 공시 도구로 답하세요."}
    if name != "capital_changes":
        return tools15.run_tool(name, args)
    keep, tools15.MAX_ROWS = tools15.MAX_ROWS, 10_000  # 5년 치가 오름차순으로 온다 → 다 받아서
    try:
        r = tools15.run_tool(name, args)
    finally:
        tools15.MAX_ROWS = keep
    if "rows" not in r:
        return r
    rows = [
        x for x in r["rows"] if x["isu_dcrs_de"].startswith(str(args["year"]))
    ]  # 요청 연도만 남기고 자른다
    return {"rows": rows[:keep], "total": len(rows)}


__all__ = ["ROOT", "TOOLS3", "TOOLS15", "TOOLS40", "run_tool"]
