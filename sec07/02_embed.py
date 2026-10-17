"""7편 ② 청크마다 임베딩(숫자 1,536개짜리 벡터)을 만들어 한 파일에 저장한다.
사용: uv run python sec07/02_embed.py → data/rag/emb.npy"""

import json
import os
import time

import numpy as np
from rag import DIR, embed

chunks = [json.loads(line) for line in (DIR / "chunks.jsonl").open(encoding="utf-8")]
t0 = time.time()
vecs, tokens, cost = embed([c["text"] for c in chunks])
emb = np.array(vecs, dtype=np.float32)
np.save(DIR / "emb.npy", emb)
print(f"모델 {os.environ['EMBED_MODEL']} · 청크 {len(chunks):,}개 → 벡터 {emb.shape[0]:,} × {emb.shape[1]:,}")
print(
    f"토큰 {tokens:,} · ${cost:.4f} · {time.time() - t0:.0f}초 · 파일 {emb.nbytes / 1e6:.1f}MB → data/rag/emb.npy"
)
