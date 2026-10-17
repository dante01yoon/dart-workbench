"""검색 3종: 한국어 bigram BM25, 벡터(코사인), RRF 하이브리드. 필터: 회사·연도.

라이브러리 없이 원리를 그대로 구현한다(강의 8편). 벡터 저장은 numpy 파일(data/emb.npy),
강의 7편에서는 같은 인터페이스로 pgvector 버전을 만든다.
"""

import json
import math
import os
import re
import urllib.request
from collections import Counter, defaultdict

import numpy as np

from . import dart

DATA = dart.ROOT / "data"


def load_chunks():
    return [json.loads(l) for l in (DATA / "chunks.jsonl").open(encoding="utf-8")]


def bigrams(text):
    t = re.sub(r"\s+", "", text.lower())
    return [t[i : i + 2] for i in range(len(t) - 1)]


class BM25:
    def __init__(self, docs, k1=1.2, b=0.75):
        self.k1, self.b = k1, b
        self.len = [0] * len(docs)
        self.post = defaultdict(list)  # bigram → [(문서, 빈도)]
        for i, d in enumerate(docs):
            c = Counter(bigrams(d))
            self.len[i] = sum(c.values())
            for w, f in c.items():
                self.post[w].append((i, f))
        self.n = len(docs)
        self.avg = sum(self.len) / max(1, self.n)

    def scores(self, query):
        s = defaultdict(float)
        for w in set(bigrams(query)):
            p = self.post.get(w)
            if not p:
                continue
            idf = math.log(1 + (self.n - len(p) + 0.5) / (len(p) + 0.5))
            for i, f in p:
                s[i] += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
        return s


def embed(texts, batch=96):
    base = os.environ["OPENAI_BASE_URL"].rstrip("/")
    out = []
    for i in range(0, len(texts), batch):
        body = json.dumps({"model": os.environ["EMBED_MODEL"], "input": [t[:6000] for t in texts[i : i + batch]]}).encode()
        req = urllib.request.Request(base + "/embeddings", data=body, headers={
            "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"})
        data = json.load(urllib.request.urlopen(req, timeout=120))["data"]
        out += [d["embedding"] for d in sorted(data, key=lambda d: d["index"])]
    v = np.asarray(out, dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def embed_text(c):
    # 청크 앞에 회사·연도·섹션을 붙여 임베딩한다(무엇에 대한 표인지 숫자만으로는 모르니까)
    return f"{c['corp']} {c['year']} 사업보고서 · {c['section']}\n{c['text']}"


def load_context():
    """Contextual Retrieval 결과(청크 id → 맥락 문장). 없으면 빈 dict."""
    p = DATA / "context.jsonl"
    if not p.exists():
        return {}
    return {r["id"]: r["context"] for r in map(json.loads, p.open(encoding="utf-8")) if r.get("context")}


def build_vectors(chunks, ctx=None):
    """ctx(맥락 문장 dict)를 주면 '맥락 + 청크'를 임베딩한다(data/emb_ctx.npy)."""
    path = DATA / ("emb_ctx.npy" if ctx else "emb.npy")
    if path.exists():
        v = np.load(path)
        if len(v) == len(chunks):
            return v
    v = embed([(ctx.get(c["id"], "") + "\n" if ctx else "") + embed_text(c) for c in chunks])
    np.save(path, v)
    return v


class Searcher:
    def __init__(self, chunks, vectors=None, ctx=None):
        self.chunks = chunks
        ctx = ctx or {}
        self.bm25 = BM25([f"{ctx.get(c['id'], '')} {c['corp']} {c['section']} {c['text']}" for c in chunks])
        self.vec = vectors

    def _mask(self, corp=None, year=None):
        # "(단위 : 사)" 같은 표 캡션 조각은 뜻이 없어 벡터 검색 상위를 차지한다 → 40자 미만은 검색 대상에서 뺀다
        return [i for i, c in enumerate(self.chunks)
                if len(c["text"]) >= 40
                and (corp is None or c["corp"] in ([corp] if isinstance(corp, str) else corp))
                and (year is None or c["year"] == year)]

    def keyword(self, q, k=10, **f):
        allowed = set(self._mask(**f))
        s = self.bm25.scores(q)
        return sorted((i for i in s if i in allowed), key=lambda i: -s[i])[:k]

    def vector(self, q, k=10, **f):
        idx = np.array(self._mask(**f), dtype=int)
        if not len(idx):
            return []
        sims = self.vec[idx] @ embed([q])[0]
        return [int(idx[j]) for j in np.argsort(-sims)[:k]]

    def hybrid(self, q, k=10, depth=50, c=60, **f):
        rrf = Counter()
        for ranked in (self.keyword(q, depth, **f), self.vector(q, depth, **f)):
            for r, i in enumerate(ranked):
                rrf[i] += 1 / (c + r + 1)
        return [i for i, _ in rrf.most_common(k)]


RERANK = """질문에 답하는 데 필요한 내용이 들어 있는 자료 순서대로 번호를 골라라.
관련 없는 자료는 빼도 된다. JSON만: {"ranked": [3, 1, 7]}"""


def rerank(searcher, q, k=10, depth=20, **f):
    """하이브리드 상위 depth개를 작은 LLM이 다시 줄 세운다(목록형 재정렬). 고르지 않은 것은 원래 순서로 뒤에 붙인다."""
    from .answer import chat

    cand = searcher.hybrid(q, k=depth, **f)
    blob = "\n\n".join(f"[{n + 1}] {searcher.chunks[i]['corp']} {searcher.chunks[i]['year']} · "
                       f"{searcher.chunks[i]['section']}\n{searcher.chunks[i]['text'][:500]}" for n, i in enumerate(cand))
    raw, _ = chat([{"role": "system", "content": RERANK}, {"role": "user", "content": f"질문: {q}\n\n{blob}"}],
                  max_tokens=300, model=os.environ.get("FAST_MODEL"))
    try:
        order = [cand[n - 1] for n in json.loads(raw)["ranked"] if 0 < n <= len(cand)]
    except (json.JSONDecodeError, KeyError, TypeError):
        order = []
    seen = set(order)
    return (list(dict.fromkeys(order)) + [i for i in cand if i not in seen])[:k]


Searcher.rerank = lambda self, q, k=10, **f: rerank(self, q, k=k, **f)


COMPANIES = ["삼성전자", "SK하이닉스", "현대자동차", "카카오"]


def decompose(searcher, q, k=10, base="hybrid", **f):
    """회사 간 비교 질문을 회사별 하위 질문으로 쪼개 따로 찾고, 결과를 번갈아 합친다(9편 질의 분해).
    회사 이름이 2개 이상 나오지 않으면 그냥 base 검색."""
    corps = [c for c in COMPANIES if c in q]
    if len(corps) < 2:
        return getattr(searcher, base)(q, k=k, **f)
    rest = q
    for c in corps:
        rest = rest.replace(c, "")
    per = [getattr(searcher, base)(f"{c} {rest}", k=k, **{**f, "corp": c}) for c in corps]
    out = []
    for rank in range(k):
        for lst in per:
            if rank < len(lst) and lst[rank] not in out:
                out.append(lst[rank])
    return out[:k]


Searcher.decompose = lambda self, q, k=10, **f: decompose(self, q, k=k, **f)


DECOMPOSE = """사업보고서 검색용으로 질문을 회사별 하위 질문으로 나눠라. 비교·순위 질문이면 각 회사에 대해 무엇을 찾아야 하는지 쓴다
(예: "영업이익률이 가장 높은 회사" → 회사마다 "매출액과 영업이익"). 대상 회사: 삼성전자, SK하이닉스, 현대자동차, 카카오.
JSON만: {"subs": [{"corp": "삼성전자", "q": "삼성전자 2025년 연결 영업이익"}]}"""


def decompose_llm(searcher, q, k=10, base="hybrid", **f):
    from .answer import chat

    try:
        raw, _ = chat([{"role": "system", "content": DECOMPOSE}, {"role": "user", "content": q}],
                      max_tokens=400, model=os.environ.get("FAST_MODEL"))
        subs = [s for s in json.loads(raw)["subs"] if s.get("corp") in COMPANIES]
    except (json.JSONDecodeError, KeyError, TypeError):
        subs = []
    if len(subs) < 2:
        return getattr(searcher, base)(q, k=k, **f)
    per = [getattr(searcher, base)(s["q"], k=k, **{**f, "corp": s["corp"]}) for s in subs]
    out = []
    for rank in range(k):
        for lst in per:
            if rank < len(lst) and lst[rank] not in out:
                out.append(lst[rank])
    return out[:k]


Searcher.decompose_llm = lambda self, q, k=10, **f: decompose_llm(self, q, k=k, **f)
# 회사 간 비교는 질의 분해, 나머지는 재정렬 — 하위 질문마다 재정렬까지
Searcher.smart = lambda self, q, k=10, **f: decompose_llm(self, q, k=k, base="rerank", **f)
