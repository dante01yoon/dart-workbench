"""30편 판사 검증 지표 — 혼동 행렬 · TPR/TNR · 정밀도/재현율 · Cohen's kappa · 윌슨 95% 구간.

"양성(positive)" = 실패. 판사의 일은 실패를 잡는 것이라서 Hamel · Shreya FAQ와 같은 방향으로 둔다.
  TP 사람 실패 · 판사 실패   FN 사람 실패 · 판사 통과(놓침)
  FP 사람 통과 · 판사 실패(헛경보)   TN 사람 통과 · 판사 통과
표준 라이브러리만 쓴다.
"""

from math import sqrt

Z = 1.96


def confusion(human, judge):
    """human · judge: {id: True(통과)/False(실패)} → 같은 id만 센다"""
    ids = [i for i in human if judge.get(i) is not None]
    c = {"TP": 0, "FN": 0, "FP": 0, "TN": 0}
    for i in ids:
        h, j = human[i], judge[i]
        c["TP" if (not h and not j) else "FN" if not h else "FP" if not j else "TN"] += 1
    return c


def rate(a, b):
    return a / (a + b) if a + b else float("nan")


def tpr(c):  # = 재현율(recall): 사람이 실패라고 한 것 중 판사가 잡은 비율
    return rate(c["TP"], c["FN"])


def tnr(c):  # 사람이 통과라고 한 것 중 판사도 통과시킨 비율
    return rate(c["TN"], c["FP"])


def precision(c):  # 판사가 실패라고 한 것 중 진짜 실패 비율
    return rate(c["TP"], c["FP"])


def agree(c):
    return (c["TP"] + c["TN"]) / sum(c.values())


def kappa(c):
    """Cohen's kappa = (관측 일치 - 우연 일치) / (1 - 우연 일치). 우연 일치 = 두 사람이 각자 비율대로 아무렇게나 찍을 때의 일치"""
    n = sum(c.values())
    po = agree(c)
    h_fail, j_fail = (c["TP"] + c["FN"]) / n, (c["TP"] + c["FP"]) / n
    pe = h_fail * j_fail + (1 - h_fail) * (1 - j_fail)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def wilson(k, n):
    """비율 k/n의 윌슨 95% 구간 — 0/n · n/n처럼 끝에 붙은 값도 폭이 나온다(31편 √(p(1-p)/n)은 여기서 0이 된다)"""
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + Z * Z / n
    mid = (p + Z * Z / (2 * n)) / d
    half = Z * sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return max(0.0, mid - half), min(1.0, mid + half)


def summary(c):
    pos, neg = c["TP"] + c["FN"], c["TN"] + c["FP"]
    return {
        **c,
        "n": sum(c.values()),
        "agree": agree(c),
        "tpr": tpr(c),
        "tpr_ci": wilson(c["TP"], pos),
        "tnr": tnr(c),
        "tnr_ci": wilson(c["TN"], neg),
        "precision": precision(c),
        "kappa": kappa(c),
    }


if __name__ == "__main__":  # 자체 점검: 항상 통과 판사는 일치율이 높아도 kappa 0, TPR 0
    h = {i: i >= 5 for i in range(100)}  # 실패 5 · 통과 95
    s = summary(confusion(h, {i: True for i in h}))
    assert s["agree"] == 0.95 and s["tpr"] == 0 and abs(s["kappa"]) < 1e-12, s
    assert summary(confusion(h, h))["kappa"] == 1
    lo, hi = wilson(5, 5)
    assert 0.56 < lo < 0.57 and hi == 1.0, (lo, hi)
    print("metrics ok")
