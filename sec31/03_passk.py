"""31편 ③ pass@k vs pass^k — 같은 문항을 k번 시켰을 때 '한 번이라도' vs '매번'. 모델 호출 없음.

10/18 처음 버전에 같은 20문항을 세 번 시킨 기록(data/repeat3_1018.json).
판정은 그날 코드 채점기(22편 정정판 v2, 기록의 ok). 사람이 읽고 거절로 본 답 3개는 따로 센다.
사용: uv run python sec31/03_passk.py
"""

from collections import Counter

from stats import READ_AS_REFUSAL, load_repeat3, mean, pass_at_k, pass_hat_k, pct

r = load_repeat3()
n = 3
c = {q: sum(v.values()) for q, v in r.items()}
print("같은 20문항 × 3회(10/18 처음 버전) · 판정: 그날 코드 채점기 v2")
print(
    "  문항별 맞은 횟수:",
    " · ".join(f"{k}번 {v}문항" for k, v in sorted(Counter(c.values()).items(), reverse=True)),
)
print(
    "  다 틀린 문항:",
    ", ".join(q for q, v in c.items() if v == 0),
    "/ 한두 번만:",
    ", ".join(q for q, v in c.items() if 0 < v < n),
)
for k in (1, 2, 3):
    pa = mean([pass_at_k(n, x, k) for x in c.values()])
    ph = mean([pass_hat_k(n, x, k) for x in c.values()])
    print(f"  k={k}: pass@{k}(한 번이라도) {pct(pa):>6}   pass^{k}(매번) {pct(ph):>6}")
p1 = mean([x / n for x in c.values()])
print(
    f"\n  시도마다 독립이라면 pass^3 = {p1:.3f}³ = {pct(p1**3)} — 실제 {pct(mean([x == n for x in c.values()]))}"
)
print(
    "  → 실패가 몇 문항에 몰려 있다(문항마다 성공률이 다르다). 평균 하나로 pass^k를 짐작하지 말고 문항별로 센다"
)

h = {q: sum(v | int((q, k) in READ_AS_REFUSAL) for k, v in rs.items()) for q, rs in r.items()}
print(
    f"\n사람이 읽은 대로(채점기가 놓친 거절 답 3개 정정): pass@3 {sum(x > 0 for x in h.values())}/20 · pass^3 {sum(x == n for x in h.values())}/20"
)
print(
    f"그날 채점기 그대로:                           pass@3 {sum(x > 0 for x in c.values())}/20 · pass^3 {sum(x == n for x in c.values())}/20"
)
