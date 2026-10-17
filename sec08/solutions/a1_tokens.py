"""과제 1 풀이: BM25 토큰을 띄어쓰기 · 2글자 · 3글자로 바꾸면? (LLM 없음, 비용 0)
사용: uv run python sec08/solutions/a1_tokens.py"""

import re

import _lab  # noqa: F401
from search import BM25, doc_text, eval_questions, first_hit, keyword, load_store


def spaces(t):
    return t.lower().split()


def trigrams(t):
    t = re.sub(r"\s+", "", t.lower())
    return [t[i : i + 3] for i in range(len(t) - 2)]


chunks, _ = load_store()
qs = eval_questions()
for name, tok in (("띄어쓰기", spaces), ("2글자", None), ("3글자", trigrams)):
    bm = BM25([doc_text(c) for c in chunks], **({"tok": tok} if tok else {}))
    line = f"{name:5s} 토큰 {len(bm.post):7,}종"
    for field in ("q", "q_para"):
        hits = [first_hit(chunks, keyword(bm, chunks, q[field], k=10, corp=q["corp"]), q) for q in qs]
        line += f"  {'원래' if field == 'q' else '말 바꿈'} recall@5 {sum(h is not None and h < 5 for h in hits) / len(qs):.3f}"
    print(line)
