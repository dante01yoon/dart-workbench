"""8편의 하이브리드 검색을 LlamaIndex로 (강의 11편).

TextNode(임베딩 미리 넣음) → VectorStoreIndex, BM25Retriever(bm25s) → QueryFusionRetriever(reciprocal_rerank, 질문 재생성 없음).
버전: llama-index-core 0.14 / llama-index-retrievers-bm25 0.8
"""

import os
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llama_index.core import VectorStoreIndex  # noqa: E402
from llama_index.core.llms import MockLLM  # noqa: E402
from llama_index.core.retrievers import QueryFusionRetriever  # noqa: E402
from llama_index.core.retrievers import BaseRetriever  # noqa: E402
from llama_index.core.schema import NodeWithScore, TextNode  # noqa: E402
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters  # noqa: E402
from llama_index.embeddings.openai_like import OpenAILikeEmbedding  # noqa: E402
from llama_index.retrievers.bm25 import BM25Retriever  # noqa: E402

from dart_rag import dart  # noqa: E402,F401
from dart_rag.search import bigrams, load_chunks  # noqa: E402

CHUNKS = load_chunks()
EMB = np.load(dart.ROOT / "data" / "emb.npy")
NODES = [TextNode(id_=str(i), text=f"{c['corp']} {c['section']} {c['text']}", embedding=EMB[i].tolist(),
                  metadata={"i": i, "corp": c["corp"], "year": c["year"]},
                  excluded_embed_metadata_keys=["i", "corp", "year"], excluded_llm_metadata_keys=["i"])
         for i, c in enumerate(CHUNKS) if len(c["text"]) >= 40]
embed = OpenAILikeEmbedding(model_name=os.environ["EMBED_MODEL"], api_base=os.environ["OPENAI_BASE_URL"], api_key=os.environ["OPENAI_API_KEY"])
index = VectorStoreIndex(NODES, embed_model=embed)  # 노드에 임베딩이 있으면 다시 만들지 않는다


def filters(corp, year):
    fs = [ExactMatchFilter(key=k, value=v) for k, v in (("corp", corp), ("year", year)) if v is not None]
    return MetadataFilters(filters=fs) if fs else None


class BigramBM25(BaseRetriever):
    """llama-index-retrievers-bm25 0.8의 tokenizer 인자는 '지원 종료 예정' 경고만 내고 무시된다(bm25s가 token_pattern으로 자른다).
    → 노드 본문과 질문을 미리 "띄어 쓴 bigram"으로 바꿔 넣는다. 형태소 분석(stemming)은 영어용이라 끈다."""

    def __init__(self, nodes):
        super().__init__()
        self.orig = {n.id_: n for n in nodes}
        bnodes = [TextNode(id_=n.id_, text=" ".join(bigrams(n.text)), metadata=n.metadata) for n in nodes]
        self.inner = BM25Retriever.from_defaults(nodes=bnodes, similarity_top_k=10, skip_stemming=True, token_pattern=r"(?u)\S\S")

    def _retrieve(self, query_bundle):
        hits = self.inner.retrieve(" ".join(bigrams(query_bundle.query_str)))
        return [NodeWithScore(node=self.orig[h.node.id_], score=h.score) for h in hits]


@lru_cache(maxsize=None)
def bm25(corp, year, korean=True):
    nodes = [n for n in NODES if (corp is None or n.metadata["corp"] == corp) and (year is None or n.metadata["year"] == year)]
    if korean:
        return BigramBM25(nodes)
    return BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=10)


def retriever(kind, corp=None, year=None, korean=True):
    vec = index.as_retriever(similarity_top_k=10, filters=filters(corp, year))
    if kind == "keyword":
        return bm25(corp, year, korean)
    if kind == "vector":
        return vec
    return QueryFusionRetriever([bm25(corp, year, korean), vec], llm=MockLLM(), mode="reciprocal_rerank",
                                num_queries=1, similarity_top_k=10, use_async=False)


def search(q, kind="hybrid", k=10, corp=None, year=None, korean=True):
    return [n.node.metadata["i"] for n in retriever(kind, corp, year, korean).retrieve(q)[:k]]
