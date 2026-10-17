"""과제 1 풀이: 청크 크기(SIZE)를 400 · 900(본편) · 1,600자로 바꾸면 검색 성적이 어떻게 바뀔까?
청크를 다시 만들고 다시 임베딩한다(크기마다 약 $0.05). 본편 저장소(data/rag)는 건드리지 않는다.
사용: uv run python sec07/solutions/a1_size.py"""

import _lab  # noqa: F401
import rag

qs = rag.eval_questions()
qv = rag.unit(rag.embed([q["q"] for q in qs])[0])
for size in (400, 900, 1600):
    rag.SIZE = size
    chunks = rag.build_chunks()
    vecs, tokens, cost = rag.embed([c["text"] for c in chunks])
    emb = rag.unit(vecs)
    rec, mrr, _ = rag.scorecard(chunks, emb, qs, qv, True)
    print(
        f"SIZE {size:5,}  청크 {len(chunks):5,}개  recall@5 {rec / len(qs):.3f}  MRR@10 {mrr:.3f}  임베딩 ${cost:.4f}"
    )
