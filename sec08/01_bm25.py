"""8편 ① BM25 색인 만들기 + 질문 하나로 시험. 띄어쓰기 토큰과 2글자 토큰이 어떻게 다른지도 본다.
사용: uv run python sec08/01_bm25.py"""

import time

from search import BM25, bigrams, doc_text, keyword, load_store

chunks, _ = load_store()
t0 = time.time()
bm = BM25([doc_text(c) for c in chunks])
print(f"청크 {len(chunks):,}개 → 서로 다른 2글자 토큰 {len(bm.post):,}개 · {time.time() - t0:.1f}초")

q = "삼성전자의 2025년 연결 영업이익은 얼마인가?"
print(f"\n질문: {q}")
print(f"띄어쓰기 토큰: {q.split()}")
print(f"2글자 토큰:   {bigrams(q)[:14]} …")
for r, i in enumerate(keyword(bm, chunks, q, k=3, corp="삼성전자")):
    c = chunks[i]
    hit = "43,601,051" in c["text"] or "43조 6,010억" in c["text"] or "43조 6,011억" in c["text"]
    print(f"  {r + 1}위 {'✅' if hit else '  '} {c['section'][:44]}")
