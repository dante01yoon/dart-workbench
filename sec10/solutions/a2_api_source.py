"""과제 2 풀이: 숫자 질문에 재무 API 값을 발췌 하나로 함께 넣으면? (숫자 12문항)
본문 발췌 6개에 "[7] 재무 API 주요 계정(연결)" 한 줄을 더하고, 재무 API 일치 · 인용 확인을 본편(본문만)과 비교한다.
사용: uv run python sec10/solutions/a2_api_source.py"""

import re

import _lab  # noqa: F401
from cite import NUM, PROMPT, Store, api_value, chat, kind, match_api, questions, sentences

store, qs = Store(), questions()
ids = [i for i, q in qs.items() if q["type"] == "number"]


def check(s, texts):
    """cite.check_sentence와 같은 규칙. 발췌 원문 목록(texts)에 API 줄도 들어 있다."""
    refs = [int(x) for x in re.findall(r"\[(\d+)\]", s)]
    if not refs:
        return "출처 없음"
    if any(not 1 <= r <= len(texts) for r in refs):
        return "없는 번호"
    if s.lstrip().startswith("계산"):
        return "계산"
    src = "".join(texts[r - 1] for r in refs).replace(" ", "")
    nums = [n for n in NUM.findall(re.sub(r"\[\d+\]", "", s)) if len(n.replace(",", "")) >= 3]
    return "확인" if all(n in src for n in nums) else "숫자 불일치"


res = {"본문만": [0, 0, 0], "본문 + API": [0, 0, 0]}  # API 일치 문항, 인용 확인 문장, 전체 문장
for qid in ids:
    q = qs[qid]
    name, value = api_value(q["corp"], q["year"], q["q"])
    hits = store.search(q["q"], q["corp"], 6)
    texts = [store.chunks[i]["text"] for i in hits]
    ctx = "\n\n".join(
        f"[{n}] ({store.chunks[i]['corp']} · {store.chunks[i]['section']})\n{store.chunks[i]['text']}"
        for n, i in enumerate(hits, 1)
    )
    api_text = f"{name} {value:,}원"
    api_line = f"[{len(hits) + 1}] (재무 API 주요 계정 · 연결 · {q['year']}년)\n{api_text}"
    for label, c, srcs in (
        ("본문만", ctx, texts),
        ("본문 + API", ctx + "\n\n" + api_line, texts + [api_text]),
    ):
        t = chat(PROMPT.format(q=q["q"], ctx=c), max_tokens=6000)[0] or "(빈 답)"
        res[label][0] += match_api(t, value)
        if kind(t) == "답":
            checks = [check(s, srcs) for s in sentences(t)]
            res[label][1] += sum(x in ("확인", "계산") for x in checks)
            res[label][2] += len(checks)
for label, (m, ok, n) in res.items():
    print(f"{label:8s} 재무 API 일치 {m}/{len(ids)} · 인용 확인 {ok}/{n}문장")
