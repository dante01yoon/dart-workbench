"""과제 1 풀이: read_section 상한(CAP)을 2,000 · 6,000 · 20,000자로 바꿔 통과와 토큰을 잰다.
사용: uv run python sec04/solutions/a1_cap.py"""

from _lab import ctx

for cap in (2000, 6000, 20000):
    rows = ctx.run_strategy("상한", ["list_sections", "read_section", "find_in_report"], cap)
    ctx.report(f"CAP={cap:,}", "목차 + 상한 + 찾기", rows)
