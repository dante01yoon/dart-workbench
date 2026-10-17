"""도구 검색: 질문과 도구 이름·설명을 한국어 글자 2개 단위(bigram) BM25로 맞춰, 가까운 도구 k개만 고른다."""

import math
import re
from collections import Counter


def bigrams(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[0-9A-Za-z]+|[가-힣]+", text.lower()):
        out += [w] if len(w) < 2 or w.isascii() else [w[i : i + 2] for i in range(len(w) - 1)]
    return out


class ToolSearch:
    def __init__(self, tools: list[dict], k1: float = 1.2, b: float = 0.75):
        self.tools = tools
        self.docs = [
            Counter(bigrams(t["function"]["name"].replace("_", " ") + " " + t["function"]["description"]))
            for t in tools
        ]
        self.avg = sum(sum(d.values()) for d in self.docs) / len(self.docs)
        df = Counter(w for d in self.docs for w in d)
        n = len(self.docs)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
        self.k1, self.b = k1, b

    def search(self, query: str, k: int = 5) -> list[dict]:
        q = bigrams(query)
        scores = []
        for i, d in enumerate(self.docs):
            size = sum(d.values())
            s = sum(
                self.idf.get(w, 0)
                * d[w]
                * (self.k1 + 1)
                / (d[w] + self.k1 * (1 - self.b + self.b * size / self.avg))
                for w in q
            )
            scores.append((s, i))
        return [self.tools[i] for s, i in sorted(scores, reverse=True)[:k]]
