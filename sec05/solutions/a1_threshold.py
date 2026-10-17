"""과제 1 풀이: 요약 기준(THRESHOLD)을 3,000 · 12,000 토큰으로 바꿔 compact+todo를 잰다(본편 6,000).
사용: uv run python sec05/solutions/a1_threshold.py"""

from _lab import lt, show

gold = lt.truth()
for th in (3_000, 12_000):
    lt.THRESHOLD = th
    show(f"THRESHOLD={th:,}", lt.run("compact+todo", gold))
