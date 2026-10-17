"""과제 2 풀이: LlamaIndex QueryFusionRetriever의 합치는 방식(mode)을 바꾸면?
reciprocal_rerank(본편, 순위로 합침) · relative_score(점수를 0~1로 맞춰 더함) · dist_based_score(평균 · 표준편차로 맞춰 더함)
사용: uv run --group frameworks python sec11/solutions/a2_fusion_modes.py"""

import _lab  # noqa: F401
import li
from llama_index.core.llms import MockLLM
from llama_index.core.retrievers import QueryFusionRetriever
from search import eval_questions, first_hit

qs = eval_questions()
for mode in ("reciprocal_rerank", "relative_score", "dist_based_score"):
    line = f"{mode:18s}"
    for field in ("q", "q_para"):
        hits = []
        for q in qs:
            fusion = QueryFusionRetriever(
                [li.bm25(q["corp"]), li.retriever("vector", q["corp"])],
                llm=MockLLM(),
                mode=mode,
                num_queries=1,
                similarity_top_k=10,
                use_async=False,
            )
            hits.append(first_hit(li.CHUNKS, [n.node.metadata["i"] for n in fusion.retrieve(q[field])], q))
        line += f"  {'원래' if field == 'q' else '말 바꿈'} {sum(h is not None and h < 5 for h in hits) / len(qs):.3f}"
    print(line, flush=True)
