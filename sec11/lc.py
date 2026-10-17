"""11편 LangChain 버전: 8편 하이브리드 검색(키워드 BM25 + 벡터 → RRF)과 10편 출처 답을 LangChain 부품으로.

- 키워드: BM25Retriever(rank_bm25). 기본 토크나이저는 띄어쓰기 → preprocess_func로 8편의 2글자 토큰을 넣는다
- 벡터: FAISS. 7편에서 만든 임베딩(emb.npy)을 그대로 넣어 다시 만들지 않는다(비교를 공정하게)
- 하이브리드: EnsembleRetriever(RRF, c=60). LangChain 1.x에서 langchain_classic으로 옮겨졌다
- 답: 프롬프트 | ChatOpenAI | 문자열 (LCEL)
버전: langchain 1.4 · langchain-community 0.4(지원 종료 예정 경고가 뜬다) · langchain-classic 1.0
"""

import os
import sys
from functools import cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec10"))
from cite import PROMPT  # 10편 지시문을 그대로 쓴다 (sec10 → sec09 → sec08 → sec07 경로도 함께 잡힌다)
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from search import MODEL, bigrams, doc_text, load_store

CHUNKS, EMB = load_store()
DOCS = [
    Document(page_content=doc_text(c), metadata={"i": i, "corp": c["corp"]}) for i, c in enumerate(CHUNKS)
]
EMBED = OpenAIEmbeddings(
    model=os.environ["EMBED_MODEL"],
    base_url=os.environ["OPENAI_BASE_URL"],
    api_key=os.environ["OPENAI_API_KEY"],
    check_embedding_ctx_length=False,  # OpenRouter는 토큰 번호 입력을 받지 않는다 → 문자열 그대로 보낸다
)
STORE = FAISS.from_embeddings(
    [(d.page_content, EMB[i].tolist()) for i, d in enumerate(DOCS)],
    EMBED,
    metadatas=[d.metadata for d in DOCS],
)


@cache
def bm25(corp, korean=True):
    """BM25Retriever에는 메타데이터 필터가 없다 → 회사마다 따로 만든다."""
    docs = [d for d in DOCS if corp is None or d.metadata["corp"] == corp]
    return BM25Retriever.from_documents(docs, k=50, **({"preprocess_func": bigrams} if korean else {}))


def retriever(kind, corp=None, korean=True):
    f = {"filter": {"corp": corp}} if corp else {}
    vec = STORE.as_retriever(search_kwargs={"k": 50, "fetch_k": 4000, **f})
    if kind == "keyword":
        return bm25(corp, korean)
    if kind == "vector":
        return vec
    return EnsembleRetriever(retrievers=[bm25(corp, korean), vec], weights=[0.5, 0.5], c=60)


def search(q, kind="hybrid", corp=None, korean=True, k=10):
    return [d.metadata["i"] for d in retriever(kind, corp, korean).invoke(q)[:k]]


LLM = ChatOpenAI(
    model=MODEL, base_url=os.environ["OPENAI_BASE_URL"], api_key=os.environ["OPENAI_API_KEY"], max_tokens=6000
)
CHAIN = PromptTemplate.from_template(PROMPT) | LLM | StrOutputParser()


def answer(q, corp=None):
    hits = search(q, "hybrid", corp, k=6)
    ctx = "\n\n".join(
        f"[{n}] ({CHUNKS[i]['corp']} · {CHUNKS[i]['section']})\n{CHUNKS[i]['text']}"
        for n, i in enumerate(hits, 1)
    )
    return CHAIN.invoke({"q": q, "ctx": ctx}), hits
