"""31편 ② 짝 비교 · 문항 수 — 같은 문항으로 두 번 잰 점수는 문항마다 차이를 먼저 본다. 모델 호출 없음.

A. 같은 시스템 · 같은 20문항 · 세 번(10/18, 그날 채점기 v2) — 아무것도 바꾸지 않은 비교(A/A)
B. 24편 개발 20 vs 26편 같은 20문항(10/19 같은 날 같은 워크벤치)
C. 문항 수: 우리 실행에서 잰 '문항별 차이의 분산'으로 5%p · 2%p 차이를 잡으려면 몇 문항이 필요한가
사용: uv run python sec31/02_paired.py
"""

import json

from stats import DATA, Z, corr, load_dev48, load_repeat3, mde, mean, n_needed, paired, pct, se, unpaired


def line(name, a, b):
    d, su = unpaired(a, b)
    _, sp = paired(a, b)
    print(f"  {name}: {pct(mean(a))} vs {pct(mean(b))}  차이 {d * 100:+.0f}%p")
    print(f"     짝 무시 SE {su * 100:4.1f}%p → 95% {(d - Z * su) * 100:+.0f} ~ {(d + Z * su) * 100:+.0f}%p")
    print(
        f"     짝 비교 SE {sp * 100:4.1f}%p → 95% {(d - Z * sp) * 100:+.0f} ~ {(d + Z * sp) * 100:+.0f}%p   (문항 상관 {corr(a, b):.2f})"
    )
    return [x - y for x, y in zip(a, b)]


r = load_repeat3()
ids = sorted(r)
run = {k: [r[q][k] for q in ids] for k in (1, 2, 3)}
print("A. 같은 시스템 · 같은 20문항 · 세 번(10/18) — 아무것도 바꾸지 않았다")
diffs = [line(f"{i}회 vs {j}회", run[i], run[j]) for i, j in ((1, 2), (1, 3), (2, 3))]

h = json.loads((DATA / "heldout24.json").read_text())
t26 = {x["id"]: int(x["correct"]) for x in load_dev48()}
a = [int(x["correct"]) for x in h["dev"]]
b = [t26[x["id"]] for x in h["dev"]]
print("\nB. 같은 날 같은 워크벤치, 같은 20문항을 두 번(24편 → 26편)")
line("24편 vs 26편", a, b)

var_d = mean([se(d) ** 2 * len(d) for d in diffs])  # 세 쌍의 '문항별 차이' 분산 평균
print(f"\nC. 문항 수 (유의수준 5% · 검정력 80%, 문항별 차이의 분산 = {var_d:.3f} — A의 세 쌍 평균)")
for delta in (0.05, 0.02):
    print(f"  {delta * 100:.0f}%p 차이를 잡으려면: 짝 비교 {n_needed(delta, var_d):,.0f}문항")
for n in (20, 48, 67):
    print(f"  {n}문항으로 잡을 수 있는 가장 작은 차이: {mde(n, var_d) * 100:.0f}%p")
