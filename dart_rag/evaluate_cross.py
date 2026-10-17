"""회사 간 비교 문항 성적: 상위 k개 안에 '질문에 나온 모든 회사'의 정답 청크가 들어 있는 비율(coverage@k).
사용: python -m dart_rag.evaluate_cross [hybrid decompose ...]"""

import json
import sys

from .evaluate import QFILE
from .search import Searcher, build_vectors, load_chunks


def main(methods, k=10):
    chunks = load_chunks()
    s = Searcher(chunks, build_vectors(chunks))
    qs = [json.loads(l) for l in QFILE.open(encoding="utf-8") if '"gold_multi"' in l]
    for m in methods:
        full, part = 0, 0
        for q in qs:
            ids = getattr(s, m)(q["q"], k=k, year=q["year"])
            got = [c for c, g in q["gold_multi"].items()
                   if any(chunks[i]["corp"] == c and (not g["section"] or g["section"] in chunks[i]["section"])
                          and any(x in chunks[i]["text"] for x in g["contains"]) for i in ids)]
            full += len(got) == len(q["gold_multi"])
            part += len(got) / len(q["gold_multi"])
        print(f"{m:10s} 모든 회사 근거 확보 {full}/{len(qs)}  회사별 평균 {part / len(qs):.2f}  (상위 {k})")


if __name__ == "__main__":
    main(sys.argv[1:] or ["keyword", "hybrid", "decompose"])
