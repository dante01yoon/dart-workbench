"""과제 1 풀이: 도구 검색으로 몇 개를 보여 줄까? k = 1 · 3 · 5 · 8.
- 검색 재현율: 보여 준 k개 안에 정답 도구가 들어 있는 비율 (모델 없이 잰다)
- 정확도·입력 토큰: 작은 모델로 질문 20개 × 3번
사용: uv run python sec03/solutions/a1_top_k.py [모델]"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from select_lab import REPEAT, SEARCH, Q, pick

model = sys.argv[1] if len(sys.argv) > 1 else "qwen/qwen3.5-9b"
for k in (1, 3, 5, 8):
    recall = sum(w in {t["function"]["name"] for t in SEARCH.search(q, k)} for q, w in Q) / len(Q)
    qs = Q * REPEAT
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda x, k=k: pick(model, SEARCH.search(x[0], k), x[0]), qs))
    acc = sum(g == w for (g, _, _), (_, w) in zip(res, qs)) / len(qs)
    tok = sum(p for _, p, _ in res) / len(qs)
    print(f"k={k}  검색 재현율 {recall:.2f}  정확도 {acc:.2f}  입력 토큰 {tok:,.0f}")
