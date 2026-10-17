"""과제 3 풀이: 비교 질문의 LLM 하위 질문을 키워드만이 아니라 맥락 붙인 하이브리드로 찾으면? (03_cross.py가 저장한 하위 질문 재사용, 질문 임베딩만)
사용: uv run python sec09/solutions/a3_cross_hybrid.py"""

import json

import _lab  # noqa: F401
import numpy as np
from context import DIR, load_context
from search import BM25, doc_text, embed, keyword, load_store, rrf, unit, vector
from tools15 import ROOT

chunks, _ = load_store()
ctx = load_context()
emb_ctx = unit(np.load(DIR / "emb_ctx.npy"))
bm = BM25([ctx.get(c["id"], "") + " " + doc_text(c) for c in chunks])
d = json.loads((DIR / "cross.json").read_text())
qs = {
    json.loads(line)["id"]: json.loads(line)
    for line in (ROOT / "eval" / "questions.jsonl").open(encoding="utf-8")
}


def interleave(lists, k=10):
    out = []
    for r in range(k):
        for lst in lists:
            if r < len(lst) and lst[r] not in out:
                out.append(lst[r])
    return out[:k]


full = part = 0
for qid, subs in zip(d["questions"], d["subs"]):
    q = qs[qid]
    qv = unit(embed([s["q"] for s in subs])[0]) if subs else []
    lists = [
        rrf(keyword(bm, chunks, s["q"], 50, s["corp"]), vector(emb_ctx, chunks, v, 50, s["corp"]), k=10)
        for s, v in zip(subs, qv)
    ]
    ranked = interleave(lists)
    got = [
        corp
        for corp, g in q["gold_multi"].items()
        if any(
            chunks[i]["corp"] == corp
            and (not g.get("section") or g["section"] in chunks[i]["section"])
            and any(x in chunks[i]["text"] for x in g["contains"])
            for i in ranked
        )
    ]
    full += len(got) == len(q["gold_multi"])
    part += len(got) / len(q["gold_multi"])
print(
    f"LLM 분해 + 맥락 하이브리드: 모든 회사 확보 {full}/{len(d['questions'])}  회사별 평균 {part / len(d['questions']):.2f}"
)
