"""31편 과제 2 — 채점기가 놓친 거절 답 3개를 사람이 읽은 대로 고치면 1 · 2 · 3회 짝 비교와 pass^3이 어떻게 바뀌나?
사용: uv run python sec31/solutions/a2_read_as_refusal.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stats import READ_AS_REFUSAL, Z, load_repeat3, mean, paired

r = load_repeat3()
ids = sorted(r)
for name, fix in (("그날 채점기 v2", set()), ("사람이 읽은 대로", READ_AS_REFUSAL)):
    run = {k: [r[q][k] | int((q, k) in fix) for q in ids] for k in (1, 2, 3)}
    print(f"{name}: 회차별 {' · '.join(str(sum(run[k])) for k in (1, 2, 3))} / 20")
    for i, j in ((1, 2), (1, 3), (2, 3)):
        d, s = paired(run[i], run[j])
        lo, hi = d - Z * s, d + Z * s
        print(
            f"   {i}회 − {j}회 {d * 100:+.0f}%p  95% {lo * 100:+.0f} ~ {hi * 100:+.0f}%p  {'0 밖' if lo > 0 or hi < 0 else '0 포함'}"
        )
    print(
        f"   pass^3 {sum(all(run[k][n] for k in (1, 2, 3)) for n in range(20))}/20 · pass@3 {sum(any(run[k][n] for k in (1, 2, 3)) for n in range(20))}/20"
    )
wrong3 = [x for x in ids if r[x][3] == 0]
print("3회차에 틀린 문항:", ", ".join(wrong3), f"(평균 정답률 {mean([r[q][3] for q in ids]) * 100:.0f}%)")
