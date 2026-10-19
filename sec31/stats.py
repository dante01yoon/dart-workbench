"""31편 통계 도구 — 표준오차 · 95% 신뢰구간 · 부트스트랩 · 짝 비교 · 군집 표준오차 · 문항 수 · pass@k/pass^k.

공식은 Miller(2024) "Adding Error Bars to Evals"(arXiv 2411.00640, Anthropic 글의 원 논문) 식 (1)·(2)·(4)·(5)·(7)·(9)·(10).
점수는 문항마다 0(틀림) · 1(맞음). 외부 라이브러리 없이 표준 라이브러리만 쓴다.
"""

import json
import random
import re
from math import comb, sqrt
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
Z = 1.96  # 95% 신뢰구간: 평균 ± 1.96 × 표준오차


def mean(xs):
    return sum(xs) / len(xs)


def se_p(xs):
    """정답률(0/1 점수)의 표준오차 = √(p(1-p)/n) (식 2)"""
    p = mean(xs)
    return sqrt(p * (1 - p) / len(xs))


def se(xs):
    """일반 점수(예: 문항별 차이 -1 · 0 · 1)의 표준오차 = √(표본분산/n) (식 1 · 7)"""
    m, n = mean(xs), len(xs)
    return sqrt(sum((x - m) ** 2 for x in xs) / (n - 1) / n)


def ci(xs):
    m, s = mean(xs), se_p(xs)
    return m - Z * s, m + Z * s


def bootstrap(xs, b=10000, seed=31):
    """문항을 다시 뽑아(복원 추출) 평균을 b번 → 가운데 95%."""
    rng = random.Random(seed)
    n = len(xs)
    ms = sorted(mean([xs[rng.randrange(n)] for _ in range(n)]) for _ in range(b))
    return ms[int(b * 0.025)], ms[int(b * 0.975) - 1]


def clustered_se(xs, groups):
    """같은 묶음(같은 문항의 답 여러 개, 같은 회사)은 함께 맞고 함께 틀린다 → 묶음별 편차 합으로 잰다(식 4)."""
    m, n = mean(xs), len(xs)
    tot = {}
    for x, g in zip(xs, groups):
        tot[g] = tot.get(g, 0) + (x - m)
    return sqrt(sum(v * v for v in tot.values())) / n


def unpaired(a, b):
    """다른 문항(또는 짝을 무시): 차이의 표준오차 = √(SE_A² + SE_B²) (식 5)"""
    return mean(a) - mean(b), sqrt(se_p(a) ** 2 + se_p(b) ** 2)


def paired(a, b):
    """같은 문항: 문항마다 차이(a-b)를 먼저 구하고 그 표준오차 (식 7)"""
    d = [x - y for x, y in zip(a, b)]
    return mean(d), se(d)


def corr(a, b):
    ma, mb = mean(a), mean(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va, vb = sum((x - ma) ** 2 for x in a), sum((y - mb) ** 2 for y in b)
    return cov / sqrt(va * vb) if va and vb else float("nan")


def n_needed(delta, var_d, alpha=0.05, power=0.8):
    """δ만큼의 차이를 power 확률로 잡으려면 문항 몇 개? n = (z_α/2 + z_β)² · Var(차이) / δ² (식 9, K=1)"""
    z = NormalDist().inv_cdf(1 - alpha / 2) + NormalDist().inv_cdf(power)
    return z * z * var_d / delta**2


def mde(n, var_d, alpha=0.05, power=0.8):
    """문항 n개로 잡을 수 있는 가장 작은 차이(식 10)"""
    z = NormalDist().inv_cdf(1 - alpha / 2) + NormalDist().inv_cdf(power)
    return z * sqrt(var_d / n)


def pass_at_k(n, c, k):
    """n번 중 c번 맞은 문항: k번 시도해 한 번이라도 맞을 확률(비편향 추정)"""
    return 1 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n, c, k):
    """k번 시도해 k번 모두 맞을 확률(pass^k)"""
    return comb(c, k) / comb(n, k)


COMPANIES = ("삼성전자", "SK하이닉스", "현대자동차", "카카오")


def company(q):
    q = re.sub(r"(?<!SK)하이닉스", "SK하이닉스", q.replace("현대차", "현대자동차"))
    found = [c for c in COMPANIES if c in q]
    return found[0] if len(found) == 1 else "여러 회사"


def load_dev48():
    """26편 녹화 실행(10/19) 중 시험지 v2 개발 48문항의 정답 여부"""
    split = {
        json.loads(line)["id"]: json.loads(line)["split"]
        for line in (ROOT / "eval" / "questions_v2_locked.jsonl").open()
    }
    rows = [json.loads(line) for line in (DATA / "traces26.jsonl").open()]
    return [x for x in rows if split.get(x["id"]) == "dev"]


def load_repeat3():
    """10/18 처음 버전 같은 20문항 × 3회. ok = 그날 코드 채점기(22편 정정판 v2) 판정"""
    out = {}
    for x in json.loads((DATA / "repeat3_1018.json").read_text()):
        out.setdefault(x["id"], {})[x["round"]] = int(x["ok"])
    return out


# 10/18 답을 사람이 읽고 거절로 본 답 3개 — 그날 채점기 v2가 거절 문구 목록에 없어 놓쳤다(28편 v3에서 문구 추가)
READ_AS_REFUSAL = {("q54", 2), ("q54", 3), ("q51", 3)}


def pct(x):
    return f"{x * 100:.1f}%"
