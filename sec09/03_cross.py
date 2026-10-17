"""9편 ③ 회사 간 비교 질문(8개) 나눠 찾기. "삼성전자와 SK하이닉스 중 영업이익이 더 큰 곳은?"처럼 회사가 둘 이상 나오면,
한 번에 찾으면 한 회사 조각만 위로 올라오기 쉽다. 회사별 하위 질문으로 나눠 따로 찾고 번갈아 합친다.
- 한 번에: 맥락 붙인 키워드 검색(필터 없음)
- 규칙 분해: 질문에 나온 회사 이름마다 "회사 + 나머지 질문"으로, 그 회사 필터
- LLM 분해: Flash가 회사별로 무엇을 찾을지 하위 질문을 쓴다(예: 영업이익률 → 매출액과 영업이익)
지표: 상위 10개 안에 질문의 모든 회사 정답 조각이 들어 있나(모든 회사 확보), 회사별 확보 비율 평균
사용: uv run python sec09/03_cross.py → data/rag/cross.json   비교 카드: uv run python sec09/04_cards_web.py"""

import json
import re

from context import DIR, chat, load_context
from search import BM25, doc_text, keyword, load_store
from tools15 import ROOT

COMPANIES = ["삼성전자", "SK하이닉스", "현대자동차", "카카오"]
DECOMPOSE = """사업보고서 검색용으로 질문을 회사별 하위 질문으로 나눠라. 비교·순위 질문이면 각 회사에 대해 무엇을 찾아야 하는지 쓴다
(예: "영업이익률이 가장 높은 회사" → 회사마다 "매출액과 영업이익"). 대상 회사: 삼성전자, SK하이닉스, 현대자동차, 카카오.
JSON만 출력: {"subs": [{"corp": "삼성전자", "q": "삼성전자 2025년 연결 영업이익"}]}

질문: """


def interleave(lists, k=10):
    out = []
    for r in range(k):
        for lst in lists:
            if r < len(lst) and lst[r] not in out:
                out.append(lst[r])
    return out[:k]


def covered(chunks, ranked, q):
    return [
        corp
        for corp, g in q["gold_multi"].items()
        if any(
            chunks[i]["corp"] == corp
            and (not g.get("section") or g["section"] in chunks[i]["section"])
            and any(s in chunks[i]["text"] for s in g["contains"])
            for i in ranked
        )
    ]


chunks, _ = load_store()
ctx = load_context()
bm = BM25([ctx.get(c["id"], "") + " " + doc_text(c) for c in chunks])
qs = [
    json.loads(line)
    for line in (ROOT / "eval" / "questions.jsonl").open(encoding="utf-8")
    if '"gold_multi"' in line
]
runs, subs_log = {"한 번에": [], "규칙 분해": [], "LLM 분해": []}, []
for q in qs:
    runs["한 번에"].append(keyword(bm, chunks, q["q"], 10))
    corps = [c for c in COMPANIES if c in q["q"]]
    rest = q["q"]
    for c in corps:
        rest = rest.replace(c, "")
    runs["규칙 분해"].append(interleave([keyword(bm, chunks, f"{c} {rest}", 10, c) for c in corps]))
    raw, _ = chat(DECOMPOSE + q["q"])
    try:
        subs = [
            s
            for s in json.loads(re.search(r"\{.*\}", raw, re.DOTALL).group(0))["subs"]
            if s.get("corp") in COMPANIES
        ]
    except (AttributeError, json.JSONDecodeError, KeyError, TypeError):
        subs = []
    subs_log.append(subs)
    runs["LLM 분해"].append(
        interleave([keyword(bm, chunks, s["q"], 10, s["corp"]) for s in subs])
        if subs
        else runs["한 번에"][-1]
    )
out = {"questions": [q["id"] for q in qs], "subs": subs_log, "runs": runs}
for m, ranked in runs.items():
    cov = [covered(chunks, r, q) for r, q in zip(ranked, qs)]
    full = sum(len(c) == len(q["gold_multi"]) for c, q in zip(cov, qs))
    part = sum(len(c) / len(q["gold_multi"]) for c, q in zip(cov, qs)) / len(qs)
    print(f"{m:6s} 모든 회사 확보 {full}/{len(qs)}  회사별 평균 {part:.2f}  (상위 10)")
(DIR / "cross.json").write_text(json.dumps(out, ensure_ascii=False))
print("저장 → data/rag/cross.json   비교 카드: uv run python sec09/04_cards_web.py")
