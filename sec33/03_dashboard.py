"""33편 ③ 평가 대시보드 — 실행마다 회귀 · 능력 세트 결과, 문항 격자, 운영 신호를 한 화면에.
모델 호출 0. 01_gate.py --log로 쌓은 기록(data/gate33_runs.jsonl)과 02_online.py 결과를 읽는다.
사용: uv run python sec33/03_dashboard.py → http://127.0.0.1:8842
"""

import json
import sys

from regress import ROOT, runs

sys.path.insert(0, str(ROOT / "sec23"))
from page import page, serve

CSS = """<style>
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:8px 0 6px}
.tile{background:#1d2028;border:1px solid #2c303a;border-radius:14px;padding:16px 18px}
.tile .k{color:#9aa0aa;font-size:19px}.tile .v{font-size:40px;font-weight:700;margin:4px 0}.tile .s{color:#9aa0aa;font-size:17px}
.cells{display:flex;gap:3px;flex-wrap:nowrap}.c{width:22px;height:30px;border-radius:4px;background:#7fd18b}
.c.f{background:#ef7a6b}.c.r{outline:2px solid #e8e6e1;outline-offset:-2px}.gap{width:14px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:28px}
</style>"""


def build():
    xs = runs()
    reg = [x["id"] for x in xs if x["split"] == "regression"]
    cap = [x["id"] for x in xs if x["split"] == "capability"]
    hist = [json.loads(line) for line in (ROOT / "data" / "gate33_runs.jsonl").open()]
    online = json.loads((ROOT / "data" / "online33.json").read_text())
    last = hist[0]["items"]  # 첫 줄 = main
    cost = sum(x["cost"] for x in xs) / sum(last.values())
    tiles = "".join(
        f'<div class="tile"><div class="k">{k}</div><div class="v">{v}</div><div class="s">{s}</div></div>'
        for k, v, s in [
            ("회귀 세트 (관문)", f"{sum(last[i] for i in reg)}/{len(reg)}", "한 문항도 떨어지면 PR을 막는다"),
            ("능력 세트", f"{sum(last[i] for i in cap)}/{len(cap)}", "막지 않고 기록 — 올라가야 할 언덕"),
            (
                "전체 (main)",
                f"{sum(last.values()) / len(xs):.0%}",
                f"{sum(last.values())}/{len(xs)} · 코드 채점기 v3",
            ),
            ("성공 1건당 비용", f"${cost:.4f}", "26편 실행 · deepseek-v4-flash"),
        ]
    )
    rows = ""
    for h in hist:
        it = h["items"]
        lost = [i for i in reg if not it[i]]
        rows += (
            f"<tr><td>{h['label']}</td><td class=num>{sum(it[i] for i in reg)}/{len(reg)}</td>"
            f"<td class=num>{sum(it[i] for i in cap)}/{len(cap)}</td><td class=num>{sum(it.values()) / len(xs):.1%}</td>"
            f"<td class={'no' if lost else 'ok'}>{'실패' if lost else '통과'}</td><td>{' '.join(lost) or '-'}</td></tr>"
        )
    grid = "".join(
        f"<tr><td>{h['label']}</td><td><div class=cells>"
        + "".join(f'<div class="c r{"" if h["items"][i] else " f"}" title="{i}"></div>' for i in reg)
        + '<div class="gap"></div>'
        + "".join(f'<div class="c{"" if h["items"][i] else " f"}" title="{i}"></div>' for i in cap)
        + "</div></td></tr>"
        for h in hist
    )
    sig = "".join(
        f"<tr><td>{s['signal']}</td><td class=num>{s['flagged']}</td><td class=num>{s['wrong']}/{s['flagged']}</td>"
        f"<td class=num>{s['caught']}/{s['of']}</td></tr>"
        for s in online["signals"]
    )
    return page(
        "평가 대시보드",
        CSS
        + "<h1>평가 대시보드</h1><p class=sub>DART 리서치 워크벤치 · 저장된 실행 53문항(26편) · 실행마다 01_gate.py 결과 · 모델 호출 0</p>"
        + f'<div class="tiles">{tiles}</div>'
        + "<h2>실행별 관문 결과</h2><table><tr><th>실행</th><th>회귀</th><th>능력</th><th>전체</th><th>관문</th><th>떨어진 회귀 문항</th></tr>"
        + rows
        + "</table>"
        + f"<h2>문항 격자 — 테두리 = 회귀 세트 {len(reg)} · 오른쪽 = 능력 세트 {len(cap)} · 빨강 = 틀림</h2><table>{grid}</table>"
        + f"<h2>운영 신호 (정답 키 없이) — 오프라인 정답과 맞춰 보기 · 틀린 답 {online['wrong']}/{online['n']}</h2>"
        + "<table><tr><th>신호</th><th>걸린 기록</th><th>그중 틀림</th><th>틀린 답 중 잡음</th></tr>"
        + sig
        + "</table><p class=sub>운영 트래픽이 없어 26편 기록을 운영 로그라고 친 계산이다.</p>",
    )


if __name__ == "__main__":
    serve(build(), 8842)
