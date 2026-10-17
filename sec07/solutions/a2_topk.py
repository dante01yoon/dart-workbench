"""과제 2 풀이: 근거 조각을 5개 → 10개로 늘리면 답이 더 맞을까? 토큰은?
사용: uv run python sec07/solutions/a2_topk.py"""

import json

from _lab import rag04
from rag import load_store
from tools15 import ROOT

chunks, emb = load_store()
qs = {json.loads(line)["id"]: json.loads(line) for line in (ROOT / "eval" / "questions.jsonl").open()}
keys = json.loads((ROOT / "eval" / "answer_keys.json").read_text())
for k in (5, 10):
    ok_n, tok, cost = 0, 0, 0.0
    for qid in rag04.QIDS:
        q = qs[qid]
        text, _, t, c = rag04.answer(q["q"], q["corp"], chunks, emb, k=k)
        ok_n += all(any(rag04.flat(x) in rag04.flat(text) for x in g) for g in keys[qid])
        tok, cost = tok + t, cost + c
    print(f"k={k:2d}  통과 {ok_n}/{len(rag04.QIDS)}  입력 {tok:,}토큰  ${cost:.4f}")
