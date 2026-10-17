"""배포용 가벼운 검색기 (강의 22편: "512MB 서버에 올리려니 메모리가 모자라다").

로컬 Searcher는 BM25 색인을 파이썬 dict/list로 들고 있어 최대 425MB를 쓴다. 여기서는
- BM25: 어휘(bigram→번호) + 포스팅(문서 번호 int32, 미리 계산한 tf 가중치 float32)을 numpy 배열로
- 벡터: float16, mmap으로 읽기(필요한 줄만 메모리에 올라온다)
- 청크: 검색 결과에 필요한 필드만
같은 질문이면 Searcher와 같은 순위가 나와야 한다(build 후 check로 확인).

빌드: python -m dart_rag.lean build   → data/deploy/
확인: python -m dart_rag.lean check
"""

import gzip
import json
import math
import sys
from collections import Counter

import numpy as np

from . import dart
from .search import bigrams, embed, load_chunks

OUT = dart.ROOT / "data" / "deploy"
K1, B = 1.2, 0.75


def build():
    chunks = load_chunks()
    OUT.mkdir(parents=True, exist_ok=True)
    vocab, rows = {}, []
    lens = np.zeros(len(chunks), np.float32)
    for i, c in enumerate(chunks):
        cnt = Counter(bigrams(f"{c['corp']} {c['section']} {c['text']}"))
        lens[i] = sum(cnt.values())
        for w, f in cnt.items():
            rows.append((vocab.setdefault(w, len(vocab)), i, f))
    rows.sort()
    term = np.array([r[0] for r in rows], np.int32)
    doc = np.array([r[1] for r in rows], np.int32)
    tf = np.array([r[2] for r in rows], np.float32)
    avg = lens.mean()
    weight = tf * (K1 + 1) / (tf + K1 * (1 - B + B * lens[doc] / avg))  # idf를 뺀 BM25 항
    starts = np.searchsorted(term, np.arange(len(vocab) + 1)).astype(np.int64)
    df = np.diff(starts)
    idf = np.log(1 + (len(chunks) - df + 0.5) / (df + 0.5)).astype(np.float32)
    np.savez(OUT / "bm25.npz", doc=doc, weight=weight.astype(np.float32), starts=starts, idf=idf)
    (OUT / "vocab.json").write_text(json.dumps(vocab, ensure_ascii=False))
    np.save(OUT / "emb16.npy", np.load(dart.ROOT / "data" / "emb.npy").astype(np.float16))
    with gzip.open(OUT / "chunks.jsonl.gz", "wt", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps({k: c[k] for k in ("id", "corp", "year", "section", "text")}, ensure_ascii=False) + "\n")
    print(f"어휘 {len(vocab):,} · 포스팅 {len(doc):,} · 청크 {len(chunks):,} → {OUT}")


class LeanSearcher:
    def __init__(self, root=OUT):
        with gzip.open(root / "chunks.jsonl.gz", "rt", encoding="utf-8") as f:
            self.chunks = [json.loads(l) for l in f]
        z = np.load(root / "bm25.npz")
        self.doc, self.weight, self.starts, self.idf = z["doc"], z["weight"], z["starts"], z["idf"]
        self.vocab = json.loads((root / "vocab.json").read_text())
        self.vec = np.load(root / "emb16.npy", mmap_mode="r")
        self.corp = np.array([c["corp"] for c in self.chunks])
        self.year = np.array([c["year"] for c in self.chunks])
        self.ok = np.array([len(c["text"]) >= 40 for c in self.chunks])

    def _mask(self, corp=None, year=None):
        m = self.ok.copy()
        if corp:
            m &= self.corp == corp
        if year:
            m &= self.year == year
        return m

    def keyword(self, q, k=10, **f):
        score = np.zeros(len(self.chunks), np.float32)
        for w in set(bigrams(q)):
            t = self.vocab.get(w)
            if t is None:
                continue
            a, b = self.starts[t], self.starts[t + 1]
            np.add.at(score, self.doc[a:b], self.idf[t] * self.weight[a:b])
        m = self._mask(**f) & (score > 0)
        idx = np.flatnonzero(m)
        return [int(i) for i in idx[np.argsort(-score[idx], kind="stable")][:k]]

    def vector(self, q, k=10, **f):
        idx = np.flatnonzero(self._mask(**f))
        if not len(idx):
            return []
        sims = np.asarray(self.vec[idx], np.float32) @ embed([q])[0]
        return [int(idx[j]) for j in np.argsort(-sims)[:k]]

    def hybrid(self, q, k=10, depth=50, c=60, **f):
        rrf = Counter()
        for ranked in (self.keyword(q, depth, **f), self.vector(q, depth, **f)):
            for r, i in enumerate(ranked):
                rrf[i] += 1 / (c + r + 1)
        return [i for i, _ in rrf.most_common(k)]


def check():
    """로컬 Searcher와 키워드 순위가 같은지, 하이브리드 상위 5가 얼마나 겹치는지."""
    import resource

    from .search import Searcher, build_vectors

    lean = LeanSearcher()
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024
    print(f"LeanSearcher 로드 후 최대 메모리 ≈ {rss:.0f}MB (macOS ru_maxrss)")
    full = Searcher(load_chunks(), build_vectors(load_chunks()))
    qs = [json.loads(l) for l in (dart.ROOT / "eval" / "questions.jsonl").open(encoding="utf-8") if '"gold": {' in l]
    same_kw = overlap = 0
    for q in qs:
        f = {"corp": q["corp"], "year": q["year"]}
        same_kw += lean.keyword(q["q"], 10, **f) == full.keyword(q["q"], 10, **f)
        overlap += len(set(lean.hybrid(q["q"], 5, **f)) & set(full.hybrid(q["q"], 5, **f))) / 5
    print(f"키워드 상위 10 순위 일치 {same_kw}/{len(qs)} · 하이브리드 상위 5 겹침 평균 {overlap / len(qs):.2f}")


if __name__ == "__main__":
    {"build": build, "check": check}[sys.argv[1]]()
