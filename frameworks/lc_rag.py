"""8편의 하이브리드 검색을 LangChain으로 (강의 11편).

BM25Retriever(키워드) + FAISS(벡터) → EnsembleRetriever(RRF). 임베딩은 직접 만든 data/emb.npy를 그대로 넣는다(비교를 공정하게).
버전: langchain 1.4 / langchain-classic(EnsembleRetriever가 여기로 옮겨짐) / langchain-community 0.4(지원 종료 예정 경고)
"""

import os
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_classic.retrievers import EnsembleRetriever  # noqa: E402
from langchain_community.retrievers import BM25Retriever  # noqa: E402
from langchain_community.vectorstores import FAISS  # noqa: E402
from langchain_core.documents import Document  # noqa: E402
from langchain_openai import OpenAIEmbeddings  # noqa: E402

from dart_rag import dart  # noqa: E402,F401  (.env 로드)
from dart_rag.search import bigrams, load_chunks  # noqa: E402

CHUNKS = [c for c in load_chunks()]
KEEP = [i for i, c in enumerate(CHUNKS) if len(c["text"]) >= 40]  # 직접 구현과 같은 조건
DOCS = [Document(page_content=f"{CHUNKS[i]['corp']} {CHUNKS[i]['section']} {CHUNKS[i]['text']}",
                 metadata={"i": i, "corp": CHUNKS[i]["corp"], "year": CHUNKS[i]["year"]}) for i in KEEP]
EMB = np.load(dart.ROOT / "data" / "emb.npy")

embeddings = OpenAIEmbeddings(model=os.environ["EMBED_MODEL"], base_url=os.environ["OPENAI_BASE_URL"],
                              api_key=os.environ["OPENAI_API_KEY"],
                              check_embedding_ctx_length=False)  # OpenRouter는 토큰 ID 입력을 받지 않는다 → 문자열로 보내기
store = FAISS.from_embeddings([(d.page_content, EMB[d.metadata["i"]].tolist()) for d in DOCS], embeddings,
                              metadatas=[d.metadata for d in DOCS])


@lru_cache(maxsize=None)
def bm25(corp, year, korean=True):
    # BM25Retriever에는 메타데이터 필터가 없다 → 회사·연도별로 따로 만든다
    docs = [d for d in DOCS if (corp is None or d.metadata["corp"] == corp) and (year is None or d.metadata["year"] == year)]
    return BM25Retriever.from_documents(docs, k=10, **({"preprocess_func": bigrams} if korean else {}))


def retriever(kind, corp=None, year=None, korean=True):
    f = {k: v for k, v in {"corp": corp, "year": year}.items() if v is not None}
    vec = store.as_retriever(search_kwargs={"k": 10, "fetch_k": 4000, **({"filter": f} if f else {})})
    if kind == "keyword":
        return bm25(corp, year, korean)
    if kind == "vector":
        return vec
    return EnsembleRetriever(retrievers=[bm25(corp, year, korean), vec], weights=[0.5, 0.5], c=60)


def search(q, kind="hybrid", k=10, corp=None, year=None, korean=True):
    return [d.metadata["i"] for d in retriever(kind, corp, year, korean).invoke(q)[:k]]
