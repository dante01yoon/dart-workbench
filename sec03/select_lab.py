"""3편 도구 선택 실험의 공통 부분: 질문 20개, 도구 검색, 모델에게 도구 하나를 고르게 하는 pick()."""

import json
import os
import urllib.request

from tool_search import ToolSearch
from tools40 import TOOLS40

Q = [  # 2편 02_select.py와 같은 질문 20개 (질문, 정답 도구)
    ("삼성전자 대표이사가 누구야?", "company_info"),
    ("카카오 본사 주소 알려줘", "company_info"),
    ("SK하이닉스 2025년 영업이익", "key_accounts"),
    ("현대자동차 2025년 자산총계는?", "key_accounts"),
    ("삼성전자 2025년 주당 배당금", "dividends"),
    ("카카오 배당성향은 몇 %야? 2025년", "dividends"),
    ("현대자동차 최대주주 지분율 2025", "largest_shareholders"),
    ("카카오 최대주주가 바뀐 적 있어? 2025년 기준", "largest_shareholder_changes"),
    ("SK하이닉스 소액주주 비율 2025", "minority_shareholders"),
    ("삼성전자 등기임원 명단 2025", "executives"),
    ("현대자동차 직원 평균 연봉 2025", "employees"),
    ("카카오 2025년 직원 수", "employees"),
    ("SK하이닉스에서 5억 넘게 받은 임원 2025", "executive_pay"),
    ("삼성전자 감사의견 2025", "auditor_opinion"),
    ("카카오 2025년 자사주 소각했어?", "treasury_stock"),
    ("현대자동차 2025년 ROE", "financial_ratios"),
    ("삼성전자 2025 영업이익률", "financial_ratios"),
    ("삼성전자 2025년 공시 목록", "list_filings"),
    ("SK하이닉스 2025년 현금흐름표의 재고자산 변동", "all_financial_statements"),
    ("현대자동차 2025 재고자산 금액", "all_financial_statements"),
]
REPEAT = 3
SEARCH = ToolSearch(TOOLS40)


def pick(model, tools, q):
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "질문에 답하려면 도구를 정확히 하나 골라 호출하라."},
            {"role": "user", "content": q},
        ],
        "tools": tools,
        "tool_choice": "required",
        "max_tokens": 300,
        "reasoning": {"effort": "none"},
        "usage": {"include": True},
    }
    req = urllib.request.Request(
        os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
            "Content-Type": "application/json",
        },
    )
    for attempt in range(3):  # 가끔 응답이 멈추는 공급자가 있어 두 번까지 다시 시도
        try:
            r = json.load(urllib.request.urlopen(req, timeout=60))
            break
        except OSError:
            if attempt == 2:
                raise
    m = r["choices"][0]["message"]
    name = ((m.get("tool_calls") or [{}])[0].get("function") or {}).get("name")
    u = r.get("usage", {})
    return name, u.get("prompt_tokens", 0), u.get("cost", 0)
