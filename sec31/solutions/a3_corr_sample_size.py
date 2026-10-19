"""31편 과제 3 — 두 버전의 문항 점수 상관이 0 · 0.3 · 0.5 · 0.7일 때, 정답률 80% 근처에서 5%p 차이를 잡으려면 몇 문항?
Anthropic 글: 최신 모델끼리 문항 점수 상관은 대개 0.3~0.7. 상관이 클수록 짝 비교가 유리하다.
Var(차이) = Var(A) + Var(B) - 2·상관·SD(A)·SD(B), 0/1 점수 Var = p(1-p).
사용: uv run python sec31/solutions/a3_corr_sample_size.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stats import mde, n_needed

p = 0.8
v = p * (1 - p)
for rho in (0.0, 0.3, 0.5, 0.7):
    var_d = 2 * v - 2 * rho * v
    print(
        f"  상관 {rho:.1f}: Var(차이) {var_d:.3f} → 5%p 잡기 {n_needed(0.05, var_d):,.0f}문항 · 48문항 최소 차이 {mde(48, var_d) * 100:.0f}%p"
    )
