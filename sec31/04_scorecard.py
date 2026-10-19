"""31편 ④ 신뢰구간이 붙은 성적표 — 01~03의 숫자를 막대 한 장으로. 모델 호출 없음.
사용: uv run python sec31/04_scorecard.py → http://127.0.0.1:8837
"""

import json
import sys
from math import sqrt

from stats import (
    DATA,
    ROOT,
    Z,
    ci,
    load_dev48,
    load_repeat3,
    mde,
    mean,
    n_needed,
    paired,
    pass_at_k,
    pass_hat_k,
    se,
    unpaired,
)

sys.path.insert(0, str(ROOT / "sec23"))
from page import page, serve

CSS = """<style>
.row{display:grid;grid-template-columns:400px 1fr 330px;align-items:center;gap:18px;padding:9px 0;border-bottom:1px solid #2c303a}
.axis{position:relative;height:34px;background:#1d2028;border-radius:8px}
.wh{position:absolute;top:13px;height:8px;border-radius:4px;background:#f2b84b}
.wh.gray{background:#6b7280}.wh.dash{background:repeating-linear-gradient(90deg,#6b7280 0 10px,transparent 10px 16px)}
.pt{position:absolute;top:5px;width:24px;height:24px;margin-left:-12px;border-radius:50%;background:#e8e6e1;border:3px solid #14161c}
.zero{position:absolute;top:-4px;bottom:-4px;width:2px;background:#ef7a6b}
.ticks{display:flex;justify-content:space-between;color:#9aa0aa;font-size:17px;margin:0 0 4px}
.lab b{font-size:22px}.lab span{display:block;color:#9aa0aa;font-size:17px}
</style>"""


def row(label, sub, p, lo, hi, lo_ax, hi_ax, cls="", note=""):
    f = lambda x: (x - lo_ax) / (hi_ax - lo_ax) * 100
    lo, hi = max(lo, lo_ax), min(hi, hi_ax)
    zero = f'<i class="zero" style="left:{f(0):.1f}%"></i>' if lo_ax < 0 else ""
    pt = f'<i class="pt" style="left:{f(p):.1f}%"></i>' if p is not None else ""
    return (
        f'<div class="row"><div class="lab"><b>{label}</b><span>{sub}</span></div>'
        f'<div class="axis">{zero}<i class="wh {cls}" style="left:{f(lo):.1f}%;width:{f(hi) - f(lo):.1f}%"></i>{pt}</div>'
        f'<div class="num">{note}</div></div>'
    )


def ticks(vals):
    return (
        '<div class="row"><div></div><div class="ticks">'
        + "".join(f"<span>{v}</span>" for v in vals)
        + "</div><div></div></div>"
    )


def build():
    dev = [int(x["correct"]) for x in load_dev48()]
    h = json.loads((DATA / "heldout24.json").read_text())
    seen, new = [int(x["correct"]) for x in h["dev"]], [int(x["correct"]) for x in h["new"]]
    r = load_repeat3()
    ids = sorted(r)
    run = {k: [r[q][k] for q in ids] for k in (1, 2, 3)}
    t26 = {x["id"]: int(x["correct"]) for x in load_dev48()}
    again = [t26[x["id"]] for x in h["dev"]]

    pct = lambda x: f"{x * 100:.0f}%"
    one = ""
    for label, sub, xs in (
        ("개발 48문항", "26편 실행 · 10/19", dev),
        ("보던 20문항", "24편 · 10/19", seen),
        ("처음 보는 20문항", "24편 · 10/19", new),
        ("같은 20문항 1회", "10/18 처음 버전 · 채점기 v2", run[1]),
        ("같은 20문항 2회", "〃", run[2]),
        ("같은 20문항 3회", "〃", run[3]),
    ):
        lo, hi = ci(xs)
        lo, hi = max(lo, 0), min(hi, 1)  # 공식(정규 근사)은 끝(100%) 근처에서 100%를 넘긴다 → 잘라서 보인다
        one += row(
            label,
            sub,
            mean(xs),
            lo,
            hi,
            0,
            1,
            note=f"{sum(xs)}/{len(xs)} = {pct(mean(xs))} <span class=sub>({pct(lo)}~{pct(hi)})</span>",
        )
    w = Z * sqrt(0.8 * 0.2 / 19)
    one += row(
        "held-out 19문항",
        "열지 않음 · 80%라면 예상 폭",
        None,
        0.8 - w,
        0.8 + w,
        0,
        1,
        "dash",
        f"±{w * 100:.0f}%p",
    )

    two = ""
    pairs = [("보던 20 − 처음 보는 20", "24편 · 다른 문항(짝 없음)", *unpaired(seen, new))]
    pairs += [("24편 → 26편 같은 20", "같은 날 · 짝 비교", *paired(seen, again))]
    pairs += [
        (f"{i}회 − {j}회", "10/18 같은 시스템 · 짝 비교", *paired(run[i], run[j]))
        for i, j in ((1, 2), (1, 3), (2, 3))
    ]
    for label, sub, d, s in pairs:
        lo, hi = d - Z * s, d + Z * s
        out = lo > 0 or hi < 0
        two += row(
            label,
            sub,
            d,
            lo,
            hi,
            -0.5,
            0.5,
            "" if out else "gray",
            f"{d * 100:+.0f}%p <span class=sub>({lo * 100:+.0f}~{hi * 100:+.0f})</span> {'<b class=no>0 밖</b>' if out else '<b class=sub>0 포함</b>'}",
        )

    diffs = [[x - y for x, y in zip(run[i], run[j])] for i, j in ((1, 2), (1, 3), (2, 3))]
    var_d = mean([se(d) ** 2 * len(d) for d in diffs])
    c = {q: sum(v.values()) for q, v in r.items()}
    pk = "".join(
        f"<tr><td class=num>k={k}</td><td class=num>{mean([pass_at_k(3, x, k) for x in c.values()]) * 100:.1f}%</td>"
        f"<td class=num>{mean([pass_hat_k(3, x, k) for x in c.values()]) * 100:.1f}%</td></tr>"
        for k in (1, 2, 3)
    )
    return page(
        "신뢰구간이 붙은 성적표",
        CSS
        + "<h1>신뢰구간이 붙은 성적표</h1><p class=sub>점은 잰 값, 막대는 95% 신뢰구간(± 1.96 × 표준오차, 0~100% 밖은 자름). 모델 호출 없음 — 저장된 실행 기록만</p>"
        "<h2>정답률</h2>"
        + ticks(["0%", "25%", "50%", "75%", "100%"])
        + one
        + "<h2>차이 — 빨간 선(0)을 넘나</h2>"
        + ticks(["−50%p", "−25", "0", "+25", "+50%p"])
        + two
        + f"<h2>문항 수 (짝 비교 · 유의수준 5% · 검정력 80%)</h2><table><tr><th>질문</th><th>답</th></tr>"
        f"<tr><td>48문항으로 잡을 수 있는 가장 작은 차이</td><td class=num>{mde(48, var_d) * 100:.0f}%p</td></tr>"
        f"<tr><td>5%p 차이를 잡으려면</td><td class=num>{n_needed(0.05, var_d):,.0f}문항</td></tr>"
        f"<tr><td>2%p 차이를 잡으려면</td><td class=num>{n_needed(0.02, var_d):,.0f}문항</td></tr></table>"
        f"<p class=sub>문항별 차이의 분산 {var_d:.3f} — 10/18 같은 시스템 세 번의 짝 차이에서 잼</p>"
        f"<h2>pass@k vs pass^k (같은 20문항 × 3회, 채점기 v2)</h2><table><tr><th></th><th>pass@k 한 번이라도</th><th>pass^k 매번</th></tr>{pk}</table>"
        "<p class=sub>사람이 읽은 대로(놓친 거절 3개 정정): pass^3 15/20 · pass@3 19/20</p>",
    )


if __name__ == "__main__":
    serve(build(), 8837)
