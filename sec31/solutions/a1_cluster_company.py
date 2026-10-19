"""31편 과제 1 — 개발 48문항을 회사로 묶어 군집 표준오차를 잰다. 왜 보통 표준오차보다 작게 나오나?
사용: uv run python sec31/solutions/a1_cluster_company.py
"""

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stats import clustered_se, company, load_dev48, mean, se_p

rows = load_dev48()
xs = [int(x["correct"]) for x in rows]
gs = [company(x["q"]) for x in rows]
by = defaultdict(list)
for x, g in zip(xs, gs):
    by[g].append(x)
for g, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    print(f"  {g:6s} {sum(v):2d}/{len(v):2d} = {mean(v) * 100:5.1f}%")
print(
    f"보통 표준오차 {se_p(xs) * 100:.1f}%p · 회사로 묶은 군집 표준오차 {clustered_se(xs, gs) * 100:.1f}%p (묶음 {len(by)}개)"
)
types = [x["type"] for x in rows]
print(f"참고: 문항 유형으로 묶으면 {clustered_se(xs, types) * 100:.1f}%p (묶음 {len(set(types))}개)")
