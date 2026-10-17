"""공시 조회 도구 (강의 2·3편). OpenDART API를 도구 하나씩으로 감싼다.

TOOLS15: 실제로 동작하는 도구 15개(설명을 잘 쓴 버전)
TOOLS15_BAD: 같은 도구, 설명을 대충 쓴 버전(2편 실험)
TOOLS40: 15개 + 실제 도구 3개 + 그럴듯한 미끼 22개(3편 실험)
run_tool(name, args): 실제 호출
"""

import json

from . import dart

CORP = {"type": "string", "description": "회사 이름(예: 삼성전자)"}
YEAR = {"type": "integer", "description": "사업연도(예: 2025)"}


def _t(name, desc, props=None, required=None):
    props = props if props is not None else {"corp": CORP, "year": YEAR}
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required if required is not None else list(props)}}}


# (이름, 좋은 설명, 나쁜 설명, OpenDART 엔드포인트)
SPEC = [
    ("company_info", "기업 개황: 정식 회사명, 대표이사 이름, 설립일, 본사 주소, 업종, 결산월.", "회사 정보", "company.json"),
    ("list_filings", "공시 목록: 기간 안에 낸 공시 제목·접수번호·날짜(사업보고서, 분기보고서 등).", "공시", "list.json"),
    ("all_financial_statements", "전체 재무제표(연결): 재무상태표·손익계산서·현금흐름표의 모든 계정 금액. 세부 계정이 필요할 때.", "재무제표", "fnlttSinglAcntAll.json"),
    ("key_accounts", "주요 계정 요약: 매출액, 영업이익, 당기순이익, 자산·부채·자본 총계(당기·전기).", "재무", "fnlttSinglAcnt.json"),
    ("compare_key_accounts", "여러 회사의 주요 계정(매출액·영업이익·순이익·자산)을 한 번에 나란히 비교.", "재무 비교", "fnlttMultiAcnt.json"),
    ("financial_ratios", "재무 지표: 영업이익률·ROE·부채비율·유동비율 같은 수익성·안정성 비율.", "지표", "fnlttSinglIndx.json"),
    ("dividends", "배당: 주당 현금배당금, 배당성향, 시가배당률(당기·전기·전전기).", "배당", "alotMatter.json"),
    ("largest_shareholders", "최대주주와 특수관계인의 이름·보유 주식 수·지분율(기말 기준).", "주주", "hyslrSttus.json"),
    ("largest_shareholder_changes", "최대주주가 바뀐 이력: 변동일, 변동 사유, 변동 전후 지분율.", "주주 변동", "hyslrChgSttus.json"),
    ("minority_shareholders", "소액주주 현황: 소액주주 수와 그들이 가진 주식 비율.", "소액주주", "mrhlSttus.json"),
    ("executives", "등기·미등기 임원 명단: 이름, 직위, 담당 업무, 주요 경력.", "임원", "exctvSttus.json"),
    ("employees", "직원 현황: 사업부문별 직원 수, 평균 근속연수, 1인 평균 급여, 연간 급여 총액.", "직원", "empSttus.json"),
    ("executive_pay", "개인별 보수: 연봉 5억 원 이상 이사·감사의 이름과 보수 총액.", "보수", "hmvAuditIndvdlBySttus.json"),
    ("auditor_opinion", "회계감사인 이름과 감사의견(적정·한정 등), 핵심감사사항.", "감사", "accnutAdtorNmNdAdtOpinion.json"),
    ("treasury_stock", "자기주식 취득·처분·소각 현황(기초·변동·기말 수량).", "자사주", "tesstkAcqsDspsSttus.json"),
]
EXTRA_REAL = [
    ("capital_changes", "증자(감자) 현황: 유상·무상증자, 주식 발행일과 수량.", "증자", "irdsSttus.json"),
    ("share_count", "주식의 총수: 발행할 주식 총수, 발행 주식 총수, 유통 주식 수.", "주식 수", "stockTotqySttus.json"),
    ("other_corp_investments", "타법인 출자 현황: 다른 회사에 투자한 지분율과 장부가액.", "출자", "otrCprInvstmntSttus.json"),
]
DECOYS = [
    ("stock_price_history", "일별 주가(시가·종가·거래량) 조회."), ("analyst_target_price", "증권사 애널리스트 목표 주가와 투자의견."),
    ("esg_score", "ESG 평가 등급."), ("news_sentiment", "뉴스 감성 점수."), ("patent_search", "특허 검색."),
    ("real_estate_price", "아파트 실거래가."), ("exchange_rate", "원/달러 환율."), ("commodity_price", "원자재 가격(유가·구리)."),
    ("dividend_forecast", "내년 예상 배당금 추정치(증권사 컨센서스)."), ("shareholder_meeting_minutes", "주주총회 회의록 원문."),
    ("executive_bio_web", "웹에서 임원 프로필 검색."), ("employee_reviews", "직원 회사 리뷰(평점)."),
    ("competitor_list", "경쟁사 목록 추천."), ("industry_report", "산업 리포트 요약."), ("macro_indicator", "GDP·금리 같은 거시 지표."),
    ("bond_yield", "국고채 금리."), ("ipo_calendar", "공모주 일정."), ("insider_trading_us", "미국 SEC 내부자 거래(Form 4)."),
    ("credit_rating", "신용등급(회사채)."), ("short_interest", "공매도 잔고."), ("foreign_ownership", "외국인 보유 비율(일별)."),
    ("earnings_call_transcript", "실적 발표 콘퍼런스콜 녹취."),
]

TOOLS15 = [_t(n, g) for n, g, _, _ in SPEC]
TOOLS15_BAD = [_t(n, b) for n, _, b, _ in SPEC]
TOOLS3 = [t for t in TOOLS15 if t["function"]["name"] in ("company_info", "key_accounts", "dividends")]
TOOLS40 = TOOLS15 + [_t(n, g) for n, g, _, _ in EXTRA_REAL] + [_t(n, d) for n, d in DECOYS]
ENDPOINT = {n: ep for n, _, _, ep in SPEC + EXTRA_REAL}


def run_tool(name, args):
    """실제 OpenDART 호출. 결과는 앞 40행만(도구 결과 상한 — 4편 주제)."""
    if name not in ENDPOINT:
        raise KeyError(f"{name}은(는) 실제 도구가 아닙니다")
    corps = [args["corp"]] if isinstance(args.get("corp"), str) else args.get("corps", [])
    codes = ",".join(dart.find_corp(c)["corp_code"] for c in corps)
    p = {"corp_code": codes}
    if name == "list_filings":
        p.update(bgn_de=f"{args.get('year', 2025)}0101", end_de=f"{args.get('year', 2025)}1231")
    elif name != "company_info":
        p.update(bsns_year=str(args.get("year", 2025)), reprt_code="11011")
        if name == "all_financial_statements":
            p["fs_div"] = "CFS"
        if name == "financial_ratios":
            p["idx_cl_code"] = "M210000"  # 수익성 지표
    d = json.loads(dart._get(ENDPOINT[name], **p))
    if "list" in d:
        d["list"] = d["list"][:40]
    return d
