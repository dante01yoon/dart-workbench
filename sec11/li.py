"""11편 LlamaIndex 버전: 8편 하이브리드 검색과 10편 출처 답을 LlamaIndex 부품으로.

- 노드: TextNode에 7편 임베딩을 미리 넣는다 → VectorStoreIndex가 다시 임베딩하지 않는다
- 키워드: BM25Retriever(bm25s). tokenizer 인자는 무시되고 영어 정규식으로 자른다 → 2글자 토큰을 띄어 써서 넣는다
- 하이브리드: QueryFusionRetriever(reciprocal_rerank). 질문을 새로 만들지 않게 num_queries=1
- 답: OpenAILike LLM에 같은 지시문
버전: llama-index-core 0.14 · llama-index-retrievers-bm25 0.8
"""

import os
import sys
from functools import cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec10"))
from cite import PROMPT
from llama_index.core import VectorStoreIndex
from llama_index.core.llms import MockLLM
from llama_index.core.retrievers import BaseRetriever, QueryFusionRetriever
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.retrievers.bm25 import BM25Retriever
from search import MODEL, bigrams, doc_text, load_store

CHUNKS, EMB = load_store()
NODES = [
    TextNode(id_=str(i), text=doc_text(c), embedding=EMB[i].tolist(), metadata={"i": i, "corp": c["corp"]})
    for i, c in enumerate(CHUNKS)
]
EMBED = OpenAILikeEmbedding(
    model_name=os.environ["EMBED_MODEL"],
    api_base=os.environ["OPENAI_BASE_URL"],
    api_key=os.environ["OPENAI_API_KEY"],
)
INDEX = VectorStoreIndex(NODES, embed_model=EMBED)  # 노드에 임베딩이 있으면 다시 만들지 않는다


class BigramBM25(BaseRetriever):
    """본문과 질문을 미리 '띄어 쓴 2글자 토큰'으로 바꿔 bm25s에 넣고, 찾은 뒤 원래 노드로 돌려준다."""

    def __init__(self, nodes, k=50):
        super().__init__()
        self.orig = {n.id_: n for n in nodes}
        spaced = [TextNode(id_=n.id_, text=" ".join(bigrams(n.text)), metadata=n.metadata) for n in nodes]
        self.inner = BM25Retriever.from_defaults(
            nodes=spaced, similarity_top_k=k, skip_stemming=True, token_pattern=r"(?u)\S\S"
        )

    def _retrieve(self, query_bundle):
        hits = self.inner.retrieve(" ".join(bigrams(query_bundle.query_str)))
        return [NodeWithScore(node=self.orig[h.node.id_], score=h.score) for h in hits]


@cache
def bm25(corp, korean=True):
    nodes = [n for n in NODES if corp is None or n.metadata["corp"] == corp]
    return BigramBM25(nodes) if korean else BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=50)


def retriever(kind, corp=None, korean=True):
    f = MetadataFilters(filters=[ExactMatchFilter(key="corp", value=corp)]) if corp else None
    vec = INDEX.as_retriever(similarity_top_k=50, filters=f)
    if kind == "keyword":
        return bm25(corp, korean)
    if kind == "vector":
        return vec
    return QueryFusionRetriever(
        [bm25(corp, korean), vec],
        llm=MockLLM(),
        mode="reciprocal_rerank",
        num_queries=1,
        similarity_top_k=10,
        use_async=False,
    )


def search(q, kind="hybrid", corp=None, korean=True, k=10):
    return [n.node.metadata["i"] for n in retriever(kind, corp, korean).retrieve(q)[:k]]


LLM = OpenAILike(
    model=MODEL,
    api_base=os.environ["OPENAI_BASE_URL"],
    api_key=os.environ["OPENAI_API_KEY"],
    is_chat_model=True,
    max_tokens=6000,
)


def answer(q, corp=None):
    hits = search(q, "hybrid", corp, k=6)
    ctx = "\n\n".join(
        f"[{n}] ({CHUNKS[i]['corp']} · {CHUNKS[i]['section']})\n{CHUNKS[i]['text']}"
        for n, i in enumerate(hits, 1)
    )
    return LLM.complete(PROMPT.format(q=q, ctx=ctx)).text, hits
