"""2편 ② 도구 선택 실험: 좋은 설명 vs 나쁜 설명. 모델이 질문 20개마다 맞는 도구를 첫 번에 고르는지 잰다(도구는 실행하지 않음).
사용: uv run python sec02/02_select.py [모델]   (기본: 작은 모델 qwen/qwen3.5-9b — 차이가 잘 보인다)
"""

import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from tools15 import TOOLS, TOOLS_BAD

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen/qwen3.5-9b"
Q = [
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


def pick(tools, q):
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "질문에 답하려면 도구를 정확히 하나 골라 호출하라."},
            {"role": "user", "content": q},
        ],
        "tools": tools,
        "tool_choice": "required",
        "max_tokens": 300,
    }
    req = urllib.request.Request(
        os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
            "Content-Type": "application/json",
        },
    )
    m = json.load(urllib.request.urlopen(req, timeout=120))["choices"][0]["message"]
    return ((m.get("tool_calls") or [{}])[0].get("function") or {}).get("name")


for label, tools in (("좋은 설명", TOOLS), ("나쁜 설명", TOOLS_BAD)):
    with ThreadPoolExecutor(8) as ex:
        got = list(ex.map(lambda x, t=tools: pick(t, x[0]), Q))
    ok = sum(g == w for g, (_, w) in zip(got, Q))
    print(f"{label}: {ok}/{len(Q)} 정확  ({MODEL})")
    for g, (q, w) in zip(got, Q):
        if g != w:
            print(f"   ✗ {q}  →  {g}  (정답 {w})")
