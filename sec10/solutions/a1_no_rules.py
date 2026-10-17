"""과제 1 풀이: 지시문에서 거절 규칙(3 · 4)을 빼면 근거 없는 질문 · 투자 질문에 어떻게 답할까?
근거 없음 5 · 투자 권유 5 문항을 규칙 있는 지시문 / 뺀 지시문으로 답하게 하고 첫 줄을 나란히 본다.
사용: uv run python sec10/solutions/a1_no_rules.py"""

import _lab  # noqa: F401
import cite
from cite import Store, answer, kind, questions

NO_RULES = cite.PROMPT.split("3. ")[0] + "\n질문: {q}\n\n{ctx}"
store, qs = Store(), questions()
ids = [i for i, q in qs.items() if q["type"] in ("none", "refuse")]
rows = []
for qid in ids:
    q = qs[qid]
    with_rules, _, _ = answer(store, q["q"], q["corp"])
    keep, cite.PROMPT = cite.PROMPT, NO_RULES
    without, _, _ = answer(store, q["q"], q["corp"])
    cite.PROMPT = keep
    rows.append((q, with_rules, without))
    print(
        f"■ {q['q']}\n  규칙 있음: {with_rules.splitlines()[0][:70]}\n  규칙 없음: {without.splitlines()[0][:70]}"
    )
print(
    f"\n정해진 거절 문구로 답한 수: 규칙 있음 {sum(kind(w) != '답' for _, w, _ in rows)}/{len(rows)}"
    f" · 규칙 없음 {sum(kind(n) != '답' for _, _, n in rows)}/{len(rows)}"
)
