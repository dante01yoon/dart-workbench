"""33편 과제 2 — 운영 트레이스를 10개만 읽을 수 있다면 무엇부터 읽나: 무작위 vs 반성 먼저 vs 판사 부족 먼저.
26편 53개 기록을 운영 로그라고 치고, 10개를 뽑았을 때 만나는 틀린 답 수의 기댓값을 센다(무작위는 1만 번 뽑기). 모델 호출 0."""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from regress import runs, score

xs = runs()
ok = score(xs)
K = 10
rng = random.Random(33)
rand = sum(sum(not ok[x["id"]] for x in rng.sample(xs, K)) for _ in range(10000)) / 10000


def first(pred):
    """신호가 걸린 기록 먼저(그 안에서는 무작위), 모자라면 나머지에서 무작위 — 1만 번 평균."""
    hit, rest = [x for x in xs if pred(x)], [x for x in xs if not pred(x)]
    tot = 0
    for _ in range(10000):
        pick = rng.sample(hit, min(K, len(hit)))
        pick += rng.sample(rest, K - len(pick))
        tot += sum(not ok[x["id"]] for x in pick)
    return tot / 10000


print(f"기록 {len(xs)}개 · 틀린 답 {sum(not v for v in ok.values())}개 · {K}개만 읽는다면 만나는 틀린 답")
print(f"  무작위            {rand:.1f}개")
print(f"  반성 먼저         {first(lambda x: x['reflected']):.1f}개")
print(f"  판사 부족 먼저    {first(lambda x: any(b != '지지' for b in x['badges'])):.1f}개")
print(
    f"  둘 다 걸린 것 먼저 {first(lambda x: x['reflected'] and any(b != '지지' for b in x['badges'])):.1f}개"
)
