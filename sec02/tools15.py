"""2편 공시 조회 도구 15개 — OpenDART API를 도구 하나씩으로 감싼다.

- 도구 설명(GOOD)은 "무엇을 돌려주나 · 언제 쓰나 · 인자에 넣을 값"을 적는다. BAD는 같은 도구를 한두 단어로만 적은 것(실험용).
- 인자는 Pydantic으로 검사한다. 틀리면 예외 대신 "무엇이 틀렸고 무엇을 넣어야 하는지"를 결과로 돌려줘 모델이 고쳐 부르게 한다.
- 결과는 필요한 칸만 남기고 줄 수를 제한한다(토큰 절약).
"""

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError

ROOT = Path(__file__).resolve().parent.parent
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

CORP_CODE = {"삼성전자": "00126380", "SK하이닉스": "00164779", "현대자동차": "00164742", "카카오": "00258801"}
Corp = Literal["삼성전자", "SK하이닉스", "현대자동차", "카카오"]
Year = Literal[2024, 2025]


class CorpYear(BaseModel):
    corp: Corp
    year: Year


class CorpOnly(BaseModel):
    corp: Corp


class Statements(BaseModel):
    corp: Corp
    year: Year
    account: str | None = None  # 계정 이름 일부(예: "감가상각"). 233줄짜리 표를 다 넘기지 않게 거른다


class Compare(BaseModel):
    corps: list[Corp]
    year: Year


# (이름, 엔드포인트, 인자 모델, 좋은 설명, 나쁜 설명, 남길 칸)
SPEC = [
    (
        "company_info",
        "company.json",
        CorpOnly,
        "기업 개황: 정식 회사명, 대표이사, 설립일, 본사 주소, 업종, 결산월.",
        "회사 정보",
        ["corp_name", "ceo_nm", "est_dt", "adres", "induty_code", "acc_mt"],
    ),
    (
        "list_filings",
        "list.json",
        CorpYear,
        "공시 목록: 그해에 낸 공시의 제목·접수번호·날짜(사업보고서·분기보고서 등).",
        "공시",
        ["rcept_dt", "report_nm", "rcept_no"],
    ),
    (
        "all_financial_statements",
        "fnlttSinglAcntAll.json",
        Statements,
        "전체 재무제표(연결): 재무상태표·손익계산서·현금흐름표의 세부 계정 금액. 감가상각비·재고자산처럼 세부 계정이 필요할 때 account에 계정 이름 일부를 넣는다.",
        "재무제표",
        ["sj_nm", "account_nm", "thstrm_amount", "frmtrm_amount"],
    ),
    (
        "key_accounts",
        "fnlttSinglAcnt.json",
        CorpYear,
        "주요 계정 요약: 매출액·영업이익·당기순이익·자산·부채·자본 총계(당기·전기, 원).",
        "재무",
        ["fs_nm", "account_nm", "thstrm_amount", "frmtrm_amount"],
    ),
    (
        "compare_key_accounts",
        "fnlttMultiAcnt.json",
        Compare,
        "여러 회사의 주요 계정(매출액·영업이익·순이익·자산)을 한 번에 나란히 비교.",
        "재무 비교",
        ["corp_code", "fs_nm", "account_nm", "thstrm_amount"],
    ),
    (
        "financial_ratios",
        "fnlttSinglIndx.json",
        CorpYear,
        "재무 지표: 영업이익률·ROE 같은 수익성 비율.",
        "지표",
        ["idx_nm", "idx_val"],
    ),
    (
        "dividends",
        "alotMatter.json",
        CorpYear,
        "배당: 주당 현금배당금(원), 현금배당성향(%), 배당 총액(당기·전기·전전기).",
        "배당",
        ["se", "stock_knd", "thstrm", "frmtrm", "lwfr"],
    ),
    (
        "largest_shareholders",
        "hyslrSttus.json",
        CorpYear,
        "최대주주와 특수관계인: 이름·관계·보유 주식 수·지분율(기말).",
        "주주",
        ["nm", "relate", "trmend_posesn_stock_co", "trmend_posesn_stock_qota_rt"],
    ),
    (
        "largest_shareholder_changes",
        "hyslrChgSttus.json",
        CorpYear,
        "최대주주가 바뀐 이력: 변동일·변동 사유·변동 뒤 지분율.",
        "주주 변동",
        ["change_on", "mxmm_shrholdr_nm", "qota_rt", "change_cause"],
    ),
    (
        "minority_shareholders",
        "mrhlSttus.json",
        CorpYear,
        "소액주주 현황: 소액주주 수와 그들이 가진 주식 비율.",
        "소액주주",
        ["se", "shrholdr_co", "shrholdr_rate", "hold_stock_rate"],
    ),
    (
        "executives",
        "exctvSttus.json",
        CorpYear,
        "임원 명단: 이름·직위·등기 여부·담당 업무.",
        "임원",
        ["nm", "ofcps", "rgist_exctv_at", "chrg_job"],
    ),
    (
        "employees",
        "empSttus.json",
        CorpYear,
        "직원 현황: 부문·성별 직원 수(sm), 평균 근속연수, 1인 평균 급여.",
        "직원",
        ["fo_bbm", "sexdstn", "sm", "avrg_cnwk_sdytrn", "jan_salary_am"],
    ),
    (
        "executive_pay",
        "hmvAuditIndvdlBySttus.json",
        CorpYear,
        "개인별 보수: 연 5억 원 이상 받은 이사·감사의 이름·직위·보수 총액.",
        "보수",
        ["nm", "ofcps", "mendng_totamt"],
    ),
    (
        "auditor_opinion",
        "accnutAdtorNmNdAdtOpinion.json",
        CorpYear,
        "회계감사인 이름과 감사의견(적정·한정 등), 강조사항.",
        "감사",
        ["bsns_year", "adtor", "adt_opinion", "emphs_matter"],
    ),
    (
        "treasury_stock",
        "tesstkAcqsDspsSttus.json",
        CorpYear,
        "자기주식: 기초·취득·처분·소각·기말 수량.",
        "자사주",
        ["stock_knd", "bsis_qy", "change_qy_acqs", "change_qy_dsps", "change_qy_incnr", "trmend_qy"],
    ),
]
MAX_ROWS = 25


def _tool(name, model, desc):
    schema = model.model_json_schema()
    schema.pop("title", None)
    for p in schema.get("properties", {}).values():
        p.pop("title", None)
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": schema}}


TOOLS = [_tool(n, m, good) for n, _, m, good, _, _ in SPEC]
TOOLS_BAD = [_tool(n, m, bad) for n, _, m, _, bad, _ in SPEC]
_BY_NAME = {s[0]: s for s in SPEC}


def run_tool(name: str, args: dict) -> dict:
    if name not in _BY_NAME:
        return {"error": f"'{name}'이라는 도구는 없습니다. 쓸 수 있는 도구: {', '.join(_BY_NAME)}"}
    _, endpoint, model, _, _, keep = _BY_NAME[name]
    try:
        a = model(**args)
    except ValidationError as e:  # 모델이 고쳐 부를 수 있게 무엇이 틀렸는지 알려 준다
        return {
            "error": "인자가 잘못됐습니다",
            "details": [f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()],
            "hint": "corp는 삼성전자·SK하이닉스·현대자동차·카카오 중 하나, year는 2024 또는 2025",
        }
    corps = a.corps if isinstance(a, Compare) else [a.corp]
    p = {"crtfc_key": os.environ["DART_API_KEY"], "corp_code": ",".join(CORP_CODE[c] for c in corps)}
    if name == "list_filings":
        p.update(bgn_de=f"{a.year}0101", end_de=f"{a.year}1231", page_count=MAX_ROWS)
    elif name != "company_info":
        p.update(bsns_year=a.year, reprt_code="11011")
        if name == "all_financial_statements":
            p["fs_div"] = "CFS"
        if name == "financial_ratios":
            p["idx_cl_code"] = "M210000"
    url = f"https://opendart.fss.or.kr/api/{endpoint}?{urllib.parse.urlencode(p)}"
    d = json.load(urllib.request.urlopen(url, timeout=30))
    if d.get("status") not in ("000", None):
        return {"error": f"OpenDART {d.get('status')} {d.get('message')}"}
    if "list" not in d:  # company.json은 목록이 아니라 한 건
        return {k: d.get(k) for k in keep}
    src = d["list"]
    if isinstance(a, Statements) and a.account:
        src = [r for r in src if a.account in r.get("account_nm", "")]
    code_name = {v: k for k, v in CORP_CODE.items()}
    rows = [
        {k: (code_name.get(r.get(k), r.get(k)) if k == "corp_code" else r.get(k)) for k in keep} for r in src
    ]
    return {
        "rows": rows[:MAX_ROWS],
        "total": len(rows),
        **({"note": f"앞 {MAX_ROWS}줄만"} if len(rows) > MAX_ROWS else {}),
    }
