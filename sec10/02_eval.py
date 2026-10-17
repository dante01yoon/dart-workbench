"""10편 ② 출처 · 거절 성적표: 숫자 12 · 서술 7 · 근거 없음 5 · 투자 권유 5 = 29문항.
- 정답: 정답 키(answer_keys.json). 근거 없음 · 투자 권유 문항은 거절해야 정답
- 인용 확인: 답 문장 중 [번호]가 있고, 문장 숫자가 그 발췌에 그대로 있는 비율
- 재무 API 일치: 숫자 문항의 금액이 API 값과 0.1% 안
- 잘못 거절: 답할 수 있는 문항(숫자 · 서술)을 거절한 수
사용: uv run python sec10/02_eval.py → data/rag/cite_eval.json"""

import json
from concurrent.futures import ThreadPoolExecutor

from cite import (
    DIR,
    Store,
    answer,
    api_value,
    check_sentence,
    correct,
    keys,
    kind,
    match_api,
    questions,
    sentences,
)

TYPES = {"number": "숫자", "narrative": "서술", "none": "근거 없음", "refuse": "투자 권유"}
store, qs, ks = Store(), questions(), keys()
ids = [i for i, q in qs.items() if q["type"] in TYPES]


def run(qid):
    q = qs[qid]
    text, hits, cost = answer(store, q["q"], q["corp"])
    checks = [check_sentence(s, store.chunks, hits) for s in sentences(text)] if kind(text) == "답" else []
    api = None
    if q["type"] == "number":
        name, value = api_value(q["corp"], q["year"], q["q"])
        api = {"account": name, "value": value, "match": match_api(text, value)}
    return {
        "id": qid,
        "type": q["type"],
        "q": q["q"],
        "answer": text,
        "kind": kind(text),
        "correct": correct(text, ks[qid]),
        "hits": [store.chunks[i]["id"] for i in hits],
        "checks": checks,
        "api": api,
        "cost": cost,
    }


with ThreadPoolExecutor(4) as ex:
    rows = list(ex.map(run, ids))
for t, name in TYPES.items():
    rs = [r for r in rows if r["type"] == t]
    line = f"{name:5s} {len(rs):2d}문항  정답 {sum(r['correct'] for r in rs):2d}"
    sents = [c for r in rs for c in r["checks"]]
    if sents:
        line += f"  인용 확인 {sum(c in ('확인', '계산') for c in sents)}/{len(sents)}문장"
    if t == "number":
        line += f"  재무 API 일치 {sum(r['api']['match'] for r in rs)}/{len(rs)}"
    if t in ("number", "narrative"):
        line += f"  잘못 거절 {sum(r['kind'] != '답' for r in rs)}"
    print(line)
bad = [(r["id"], c) for r in rows for c in r["checks"] if c not in ("확인", "계산")]
print(f"인용 문제 {len(bad)}건: " + ", ".join(f"{i} {c}" for i, c in bad[:6]))
print(f"비용 ${sum(r['cost'] for r in rows):.4f}")
(DIR / "cite_eval.json").write_text(json.dumps(rows, ensure_ascii=False))
print("저장 → data/rag/cite_eval.json   하이라이트 화면: uv run python sec10/04_cite_web.py")
