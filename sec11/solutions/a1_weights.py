"""과제 1 풀이: LangChain EnsembleRetriever의 가중치(키워드 : 벡터)를 바꾸면 하이브리드가 나아질까?
사용: uv run --group frameworks python sec11/solutions/a1_weights.py"""

import _lab  # noqa: F401
import lc
from langchain_classic.retrievers import EnsembleRetriever
from search import eval_questions, first_hit

qs = eval_questions()
for w in (0.5, 0.7, 0.9):
    line = f"키워드 {w:.1f} : 벡터 {1 - w:.1f}"
    for field in ("q", "q_para"):
        hits = []
        for q in qs:
            vec = lc.STORE.as_retriever(
                search_kwargs={"k": 50, "fetch_k": 4000, "filter": {"corp": q["corp"]}}
            )
            ens = EnsembleRetriever(retrievers=[lc.bm25(q["corp"]), vec], weights=[w, 1 - w], c=60)
            hits.append(first_hit(lc.CHUNKS, [d.metadata["i"] for d in ens.invoke(q[field])[:10]], q))
        line += f"  {'원래' if field == 'q' else '말 바꿈'} {sum(h is not None and h < 5 for h in hits) / len(qs):.3f}"
    print(line, flush=True)
