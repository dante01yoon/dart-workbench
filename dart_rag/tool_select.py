"""도구 선택 실험 (강의 2·3편): 모델이 질문에 맞는 도구를 고르는가, 도구가 늘면 무엇이 변하나.

설정: 3개 / 15개(좋은 설명) / 15개(나쁜 설명) / 40개(미끼 포함) / 40개 + 도구 검색(질문과 가까운 5개만 보여 주기)
지표: 선택 정확도(첫 도구 이름이 정답), 인자 정확도(corp·year), 호출당 입력 토큰
사용: [TOOL_MODEL=qwen/qwen3.5-9b] python -m dart_rag.tool_select → data/tool_select-<모델>.json
"""

import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from . import dart, harness
from .search import BM25
from .tools import TOOLS3, TOOLS15, TOOLS15_BAD, TOOLS40

Q = [  # (질문, 정답 도구, corp, year)
    ("삼성전자 대표이사가 누구야?", "company_info", "삼성전자", None),
    ("카카오 본사 주소 알려줘", "company_info", "카카오", None),
    ("SK하이닉스 2025년 영업이익", "key_accounts", "SK하이닉스", 2025),
    ("현대자동차 2025년 자산총계는?", "key_accounts", "현대자동차", 2025),
    ("삼성전자 2025년 주당 배당금", "dividends", "삼성전자", 2025),
    ("카카오 배당성향은 몇 %야? 2025년", "dividends", "카카오", 2025),
    ("현대자동차 최대주주 지분율 2025", "largest_shareholders", "현대자동차", 2025),
    ("카카오 최대주주가 바뀐 적 있어? 2025년 기준", "largest_shareholder_changes", "카카오", 2025),
    ("SK하이닉스 소액주주 비율 2025", "minority_shareholders", "SK하이닉스", 2025),
    ("삼성전자 등기임원 명단 2025", "executives", "삼성전자", 2025),
    ("현대자동차 직원 평균 연봉 2025", "employees", "현대자동차", 2025),
    ("카카오 2025년 직원 수", "employees", "카카오", 2025),
    ("SK하이닉스에서 5억 넘게 받은 임원 2025", "executive_pay", "SK하이닉스", 2025),
    ("삼성전자 감사의견 2025", "auditor_opinion", "삼성전자", 2025),
    ("카카오 2025년 자사주 소각했어?", "treasury_stock", "카카오", 2025),
    ("현대자동차 2025년 ROE", "financial_ratios", "현대자동차", 2025),
    ("삼성전자 2025 영업이익률", "financial_ratios", "삼성전자", 2025),
    ("삼성전자 2025년 공시 목록", "list_filings", "삼성전자", 2025),
    ("SK하이닉스 2025년 현금흐름표의 감가상각비", "all_financial_statements", "SK하이닉스", 2025),
    ("현대자동차 2025 재고자산 금액", "all_financial_statements", "현대자동차", 2025),
]
SYSTEM = "한국 상장사 공시 도우미. 질문에 답하려면 도구를 정확히 하나 골라 호출하라."


def pick(tools, q):
    body = {"model": os.environ.get("TOOL_MODEL") or os.environ["FAST_MODEL"], "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": q}],
            "tools": tools, "tool_choice": "required", "max_tokens": 300, "reasoning": {"effort": "none"}, "usage": {"include": True}}
    req = urllib.request.Request(os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    harness.record(body["model"], r.get("usage", {}), 0)
    tc = (r["choices"][0]["message"].get("tool_calls") or [{}])[0].get("function", {})
    return tc.get("name"), json.loads(tc.get("arguments") or "{}"), r.get("usage", {}).get("prompt_tokens", 0)


def tool_search(tools, q, k=5):
    """도구 검색: 질문과 도구 설명을 BM25로 맞춰 상위 k개만 모델에게 보여 준다."""
    idx = BM25([t["function"]["name"].replace("_", " ") + " " + t["function"]["description"] for t in tools])
    s = idx.scores(q)
    return [tools[i] for i in sorted(s, key=lambda i: -s[i])[:k]]


def main():
    configs = [("3개", TOOLS3, False), ("15개 · 좋은 설명", TOOLS15, False), ("15개 · 나쁜 설명", TOOLS15_BAD, False),
               ("40개 · 미끼 포함", TOOLS40, False), ("40개 + 도구 검색(5개)", TOOLS40, True)]
    out = []
    for name, tools, search in configs:
        names = {t["function"]["name"] for t in tools}
        qs = [q for q in Q if q[1] in names]

        def one(item):
            q, want, corp, year = item
            shown = tool_search(tools, q) if search else tools
            got, args, ptok = pick(shown, q)
            arg_ok = args.get("corp") == corp and (year is None or args.get("year") == year)
            return {"q": q, "want": want, "got": got, "ok": got == want, "arg_ok": arg_ok, "prompt_tokens": ptok,
                    "found_in_search": want in {t["function"]["name"] for t in shown}}

        with ThreadPoolExecutor(8) as ex:
            rows = list(ex.map(one, qs))
        n = len(rows)
        res = {"config": name, "n": n, "accuracy": round(sum(r["ok"] for r in rows) / n, 3),
               "arg_accuracy": round(sum(r["arg_ok"] for r in rows) / n, 3),
               "avg_prompt_tokens": round(sum(r["prompt_tokens"] for r in rows) / n),
               "misses": [(r["q"], r["want"], r["got"]) for r in rows if not r["ok"]]}
        if search:
            res["search_recall"] = round(sum(r["found_in_search"] for r in rows) / n, 3)
        out.append(res)
        print(f"{name:22s} 정확도 {res['accuracy']:.2f}  인자 {res['arg_accuracy']:.2f}  입력 토큰 {res['avg_prompt_tokens']:5d}  ({n}문항)"
              + (f"  검색 재현율 {res['search_recall']:.2f}" if search else ""), flush=True)
        for m in res["misses"]:
            print("     ✗", m)
    (dart.ROOT / "data" / f"tool_select-{(os.environ.get('TOOL_MODEL') or os.environ['FAST_MODEL']).split('/')[-1]}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
