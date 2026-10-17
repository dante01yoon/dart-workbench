"""과제 3 풀이: 10편 성적표(숫자 12 · 근거 없음 5 · 투자 권유 5)를 LangChain 체인으로 다시 돌리면?
같은 지시문 · LangChain 하이브리드 검색 · ChatOpenAI. 정답 · 인용 확인 · 재무 API 일치 · 거절을 센다.
사용: uv run --group frameworks python sec11/solutions/a3_lc_cite_eval.py"""

from concurrent.futures import ThreadPoolExecutor

import _lab  # noqa: F401
import lc
from cite import api_value, check_sentence, correct, keys, kind, match_api, questions, sentences

qs, ks = questions(), keys()
ids = [i for i, q in qs.items() if q["type"] in ("number", "none", "refuse")]


def run(qid):
    q = qs[qid]
    text, hits = lc.answer(q["q"], q["corp"])
    checks = [check_sentence(s, lc.CHUNKS, hits) for s in sentences(text)] if kind(text) == "답" else []
    api = match_api(text, api_value(q["corp"], q["year"], q["q"])[1]) if q["type"] == "number" else None
    return q["type"], correct(text, ks[qid]), checks, api


with ThreadPoolExecutor(4) as ex:
    rows = list(ex.map(run, ids))
for t, name in (("number", "숫자"), ("none", "근거 없음"), ("refuse", "투자 권유")):
    rs = [r for r in rows if r[0] == t]
    line = f"{name:5s} {len(rs):2d}문항  정답 {sum(r[1] for r in rs):2d}"
    sents = [c for r in rs for c in r[2]]
    if sents:
        line += f"  인용 확인 {sum(c in ('확인', '계산') for c in sents)}/{len(sents)}문장"
    if t == "number":
        line += f"  재무 API 일치 {sum(r[3] for r in rs)}/{len(rs)}"
    print(line)
