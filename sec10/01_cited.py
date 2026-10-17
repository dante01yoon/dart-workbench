"""10편 ① 출처 다는 답 4가지: 숫자 · 서술 · 근거 없는 질문 · 투자 권유 질문.
문장마다 [번호]가 있는지, 번호가 발췌 범위 안인지, 문장의 숫자가 그 발췌에 그대로 있는지 확인하고,
숫자 질문은 재무 API(주요 계정, 연결) 값과도 대조한다.
사용: uv run python sec10/01_cited.py"""

from cite import Store, answer, api_value, check_sentence, kind, match_api, questions, sentences

# 카카오 영업이익 · SK하이닉스 환율 통화 · 카카오 2026년 3분기 · 카카오 주가
QIDS = ["q09", "q45", "q52", "q58"]

store, qs = Store(), questions()
total = 0.0
for qid in QIDS:
    q = qs[qid]
    text, hits, cost = answer(store, q["q"], q["corp"])
    total += cost
    print(f"■ {q['q']}  → {kind(text)}")
    for s in sentences(text):
        mark = check_sentence(s, store.chunks, hits) if kind(text) == "답" else "-"
        print(f"  [{mark}] {s}")
    if q["type"] == "number":
        name, value = api_value(q["corp"], q["year"], q["q"])
        print(f"  재무 API {name} {value:,}원 → {'일치' if match_api(text, value) else '불일치'}")
    print()
print(f"비용 ${total:.4f}")
