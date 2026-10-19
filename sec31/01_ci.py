"""31편 ① 신뢰구간 — 정답률 하나에 "얼마나 흔들릴 수 있나"를 붙인다. 모델 호출 없음(저장된 실행 기록만).

A. 시험지 v2 개발 48문항(26편 녹화 실행): 표준오차 · 95% 신뢰구간(공식) vs 부트스트랩
B. 24편 "보던 20문항 90% vs 처음 보는 20문항 75%" — 이 15%p 차이는 진짜인가
C. held-out 19문항은 열지 않는다 — 열면 신뢰구간이 얼마나 넓을지만 미리 계산
D. 같은 20문항을 세 번 = 답 60개(10/18): 답을 따로 세면 안 되는 이유(군집 표준오차)
사용: uv run python sec31/01_ci.py
"""

import json
from math import sqrt

from stats import DATA, Z, bootstrap, ci, clustered_se, load_dev48, load_repeat3, mean, pct, se_p, unpaired

dev = [int(x["correct"]) for x in load_dev48()]
p, s = mean(dev), se_p(dev)
lo, hi = ci(dev)
blo, bhi = bootstrap(dev)
print(
    f"A. 개발 48문항(26편 실행, 10/19): {sum(dev)}/{len(dev)} = {pct(p)}  (한 문항 = {100 / len(dev):.1f}%p)"
)
print(f"   표준오차 √(p(1−p)/n) = {s * 100:.1f}%p → 95% 신뢰구간 {pct(lo)} ~ {pct(hi)}")
print(f"   부트스트랩(문항을 다시 뽑아 1만 번) → {pct(blo)} ~ {pct(bhi)}")

h = json.loads((DATA / "heldout24.json").read_text())
a, b = [int(x["correct"]) for x in h["dev"]], [int(x["correct"]) for x in h["new"]]
d, sd = unpaired(a, b)
print(f"\nB. 24편: 보던 20 {pct(mean(a))} vs 처음 보는 20 {pct(mean(b))} → 차이 {d * 100:+.1f}%p")
print(f"   다른 문항이라 짝이 없다: 표준오차 √(SE₁² + SE₂²) = {sd * 100:.1f}%p")
print(
    f"   95% 신뢰구간 {(d - Z * sd) * 100:+.1f}%p ~ {(d + Z * sd) * 100:+.1f}%p → 0을 포함: 우연인지 아직 모른다"
)

w = Z * sqrt(0.8 * 0.2 / 19)
print(f"\nC. held-out 19문항(열지 않음): 정답률이 80%라면 95% 신뢰구간 ±{w * 100:.1f}%p")
print("   → 작은 개선을 재는 데 쓸 수 없다. 큰 결정 때 '무너지지 않았나'만 본다")

r = load_repeat3()
ans = [(q, v) for q in sorted(r) for v in r[q].values()]
xs = [v for _, v in ans]
print(f"\nD. 같은 20문항 × 3회 = 답 60개(10/18 처음 버전, 그날 채점기 v2): {sum(xs)}/60 = {pct(mean(xs))}")
print(f"   답 60개를 따로 세면 표준오차 {se_p(xs) * 100:.1f}%p")
print(
    f"   문항으로 묶으면(군집 표준오차) {clustered_se(xs, [q for q, _ in ans]) * 100:.1f}%p — 같은 문항의 답은 함께 맞고 함께 틀린다"
)
