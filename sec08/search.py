"""8편 공용: 키워드 검색 BM25(한국어 2글자 조각)를 직접 만들고, 7편 벡터 검색과 섞는다(RRF), 마지막에 LLM이 다시 줄 세운다(재정렬).

- 토큰: 한국어는 조사가 붙어("영업이익은", "영업이익을") 띄어쓰기로 자르면 같은 낱말이 다른 토큰이 된다.
  그래서 공백을 지우고 2글자씩 겹쳐 자른다(bigram): "영업이익" → 영업 · 업이 · 이익.
- BM25: 질문 토큰이 그 청크에 자주 나오고(tf), 다른 청크에는 드물수록(idf) 점수가 높다. 긴 청크는 조금 깎는다(b).
- RRF: 두 순위표를 1 / (60 + 순위)로 더한다. 점수 단위가 달라도 섞을 수 있다.
"""

import json
import math
import os
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec07"))
from rag import DIR, YEAR, embed, eval_questions, is_gold, load_store, unit  # noqa: F401

MODEL = os.environ.get("MODEL_RAG", "deepseek/deepseek-v4-flash")


def bigrams(text):
    t = re.sub(r"\s+", "", text.lower())
    return [t[i : i + 2] for i in range(len(t) - 1)]


class BM25:
    def __init__(self, docs, k1=1.2, b=0.75, tok=bigrams):
        self.k1, self.b, self.tok = k1, b, tok
        self.post = defaultdict(list)  # 토큰 → [(청크 번호, 그 청크에 나온 횟수)]
        self.len = []
        for i, d in enumerate(docs):
            c = Counter(tok(d))
            self.len.append(sum(c.values()))
            for w, f in c.items():
                self.post[w].append((i, f))
        self.n, self.avg = len(docs), sum(self.len) / len(docs)

    def scores(self, query):
        s = np.zeros(self.n)
        for w in set(self.tok(query)):
            p = self.post.get(w)
            if not p:
                continue
            idf = math.log(1 + (self.n - len(p) + 0.5) / (len(p) + 0.5))  # 드문 토큰일수록 크다
            for i, f in p:
                s[i] += (
                    idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
                )
        return s


def doc_text(c):
    return f"{c['corp']} {c['section']} {c['text']}"  # 키워드 검색은 회사 이름과 섹션 경로도 함께 찾는다


def allowed(chunks, corp=None):
    return np.array([corp is None or c["corp"] == corp for c in chunks])


def keyword(bm, chunks, q, k=10, corp=None):
    s = np.where(allowed(chunks, corp), bm.scores(q), -1)
    return [int(i) for i in np.argsort(-s)[:k] if s[i] > 0]


def vector(emb, chunks, qv, k=10, corp=None):
    s = np.where(allowed(chunks, corp), emb @ qv, -1)
    return [int(i) for i in np.argsort(-s)[:k]]


def rrf(*ranked, k=10, c=60):
    score = Counter()
    for lst in ranked:
        for r, i in enumerate(lst):
            score[i] += 1 / (c + r + 1)
    return [i for i, _ in score.most_common(k)]


RERANK = (
    "질문에 답하는 데 필요한 내용이 들어 있는 자료 순서대로 번호를 골라라. 관련 없는 자료는 빼도 된다. "
    'JSON만 출력: {"ranked": [3, 1, 7]}'
)


def rerank(chunks, q, cand, k=10):
    """하이브리드 후보를 LLM이 다시 줄 세운다. 고르지 않은 후보는 원래 순서대로 뒤에 붙인다. 돌려받는 것: (순위, 비용)"""
    blob = "\n\n".join(
        f"[{n + 1}] {chunks[i]['corp']} · {chunks[i]['section']}\n{chunks[i]['text'][:500]}"
        for n, i in enumerate(cand)
    )
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": RERANK},
            {"role": "user", "content": f"질문: {q}\n\n{blob}"},
        ],
        "max_tokens": 6000,  # 7편 교훈: 작으면 생각에 다 써서 빈 답이 나온다
        "usage": {"include": True},
    }
    req = urllib.request.Request(
        os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
            "Content-Type": "application/json",
        },
    )
    r = json.load(urllib.request.urlopen(req, timeout=300))
    raw = r["choices"][0]["message"].get("content") or ""
    try:
        picked = [
            cand[n - 1]
            for n in json.loads(re.search(r"\{.*\}", raw, re.DOTALL).group(0))["ranked"]
            if 0 < n <= len(cand)
        ]
    except (AttributeError, json.JSONDecodeError, KeyError, TypeError):
        picked = []  # 형식이 깨지면 하이브리드 순서 그대로
    order = list(dict.fromkeys(picked)) + [i for i in cand if i not in picked]
    return order[:k], float(r.get("usage", {}).get("cost") or 0)


def first_hit(chunks, ranked, q):
    return next((r for r, i in enumerate(ranked) if is_gold(chunks[i], q)), None)
