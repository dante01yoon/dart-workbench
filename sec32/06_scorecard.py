"""32편 ⑥ 에이전트 성적표 — 01~05의 결과를 한 화면에: 최종 답 · 검색 · 근거 · 궤적 · 레드팀 · 비용.
모델 호출 없음(저장된 결과만 읽는다). 01~05를 먼저 돌린다.
사용: uv run python sec32/06_scorecard.py → http://127.0.0.1:8838
"""

import sys

from agent_eval import DATA, ROOT, load, mrr, recall_at, traces

sys.path.insert(0, str(ROOT / "sec23"))
from page import page, serve

CSS = """<style>
.tiles{display:grid;grid-template-columns:repeat(6,1fr);gap:14px;margin:8px 0 6px}
.tile{background:#1d2028;border:1px solid #2c303a;border-radius:14px;padding:16px 18px}
.tile .k{color:#9aa0aa;font-size:19px}.tile .v{font-size:40px;font-weight:700;margin:4px 0}.tile .s{color:#9aa0aa;font-size:17px}
.bar{display:grid;grid-template-columns:150px 1fr 110px;align-items:center;gap:14px;margin:8px 0}
.track{height:22px;background:#1d2028;border-radius:6px;overflow:hidden}.fill{height:100%;background:#f2b84b}
.two{display:grid;grid-template-columns:1fr 1fr;gap:28px}
</style>"""


def pct(a, b):
    return f"{a / b * 100:.0f}%" if b else "-"


def tile(k, v, s):
    return f'<div class="tile"><div class="k">{k}</div><div class="v">{v}</div><div class="s">{s}</div></div>'


def bar(label, x, note=""):
    return f'<div class="bar"><b>{label}</b><div class="track"><div class="fill" style="width:{x * 100:.0f}%"></div></div><span class="num">{x * 100:.0f}% {note}</span></div>'


def build():
    xs = traces()
    ret, gr, tr, co = (load(f"eval32_{n}.json") for n in ("retrieval", "grounded", "trajectory", "cost"))
    rt = load("redteam32.json") if (DATA / "redteam32.json").exists() else []
    ranks = [r["rank"] for r in ret]
    correct = sum(x["correct"] for x in xs)
    nums = [r for r in gr if r["has_num"] and r["cited"]]
    sup = sum(r["judge"] == "지지" for r in gr)
    tr_ok = [r for r in tr if not r["problems"]]
    rt_ok = sum(r["passed"] for r in rt)
    tiles = "".join(
        [
            tile("① 최종 답", f"{correct}/{len(xs)}", "53문항 · 그날 채점기(22편)"),
            tile(
                "② 검색 Recall@6",
                f"{recall_at(ranks, 6) * 100:.0f}%",
                f"MRR {mrr(ranks):.2f} · {len(ranks)}문항",
            ),
            tile(
                "③ 근거 (판사 지지)",
                pct(sup, len(gr)),
                f"문장 {len(gr)} · 숫자 대조 {pct(len([r for r in nums if not r['missing']]), len(nums))}",
            ),
            tile("④ 도구 궤적", f"{len(tr_ok)}/{len(tr)}", "필요한 도구 · 인자 · 중복 · 순서"),
            tile("⑤ 레드팀", f"{rt_ok}/{len(rt)}" if rt else "-", "인젝션 · 투자 미끼 · 범위 밖"),
            tile(
                "⑥ 성공 1건당",
                f"${co['per_success']:.4f}",
                f"중앙값 {co['sec_median']:.0f}초 · p95 {co['sec_p95']:.0f}초",
            ),
        ]
    )

    retrieval = "".join(bar(f"Recall@{k}", recall_at(ranks, k)) for k in (1, 3, 6, 10))
    wrong = "".join(
        f"<tr><td>{r['id']}</td><td>{r['q'][:24]}</td><td class=num>{r['rank'] or '-'}</td>"
        f"<td>{'O' if r['in_evidence'] else 'X'}</td><td>{'O' if r['in_report'] else 'X'}</td>"
        f"<td class=no>{'채점' if r['in_report'] else '검색' if not (r['rank'] and r['rank'] <= 6) else '근거 뽑기'}</td></tr>"
        for r in ret
        if not r["correct"]
    )
    cell = lambda c, j: sum((not r["missing"]) == c and (r["judge"] == "지지") == j for r in nums)
    grounded = (
        "<table><tr><th>숫자 있는 문장</th><th>판사 지지</th><th>판사 부족</th></tr>"
        f"<tr><td>코드 통과</td><td class='num ok'>{cell(True, True)}</td><td class='num part'>{cell(True, False)}</td></tr>"
        f"<tr><td>코드 걸림</td><td class='num part'>{cell(False, True)}</td><td class='num no'>{cell(False, False)}</td></tr></table>"
        "<p class=sub>코드만 걸린 것은 대부분 계산한 숫자(증감 · 비율). 사람 판단과의 일치는 아직 재지 않았다.</p>"
    )
    tcell = lambda c, t: sum(r["correct"] == c and (not r["problems"]) == t for r in tr)
    traj = (
        "<table><tr><th></th><th>궤적 통과</th><th>궤적 문제</th></tr>"
        f"<tr><td>답 맞음</td><td class='num ok'>{tcell(True, True)}</td><td class='num part'>{tcell(True, False)}</td></tr>"
        f"<tr><td>답 틀림</td><td class='num part'>{tcell(False, True)}</td><td class='num no'>{tcell(False, False)}</td></tr></table>"
        + "".join(
            f"<p><b>{r['id']}</b> {', '.join(r['problems'])} <span class=sub>{r['q'][:26]}</span></p>"
            for r in tr
            if r["problems"]
        )
    )
    red = "".join(
        f"<tr><td>{r['id']}</td><td>{r['kind']}</td><td>{r['q'][:30]}</td>"
        f"<td class={'ok' if r['passed'] else 'no'}>{'통과' if r['passed'] else '실패'}</td><td>{r['detail']}</td></tr>"
        for r in rt
    )
    caps = "".join(
        f"<tr><td class=num>${c['cap']}</td><td class=num>{c['cut']}</td><td class=num>{c['lost']}</td></tr>"
        for c in co["caps"]
    )
    return page(
        "에이전트 성적표",
        CSS
        + "<h1>에이전트 성적표</h1><p class=sub>DART 리서치 워크벤치 · deepseek-v4-flash · 26편 실행 기록(2026-10-19) + 레드팀 9문항 실제 실행</p>"
        + f'<div class="tiles">{tiles}</div>'
        + f'<div class="two"><div><h2>② 검색 — 정답 섹션이 상위 k 안에</h2>{retrieval}'
        + f"<p class=sub>MRR {mrr(ranks):.3f} · 정답 섹션 = 첫 정답 키가 들어 있는 섹션(1~5곳)</p></div>"
        + "<div><h2>틀린 문항은 어디서 끊겼나</h2><table><tr><th></th><th>질문</th><th>순위</th><th>근거</th><th>답</th><th>문제</th></tr>"
        + wrong
        + "</table></div></div>"
        + f'<div class="two"><div><h2>③ 근거 — 코드 × 판사</h2>{grounded}</div><div><h2>④ 궤적 × 최종 답</h2>{traj}</div></div>'
        + "<h2>⑤ 레드팀 (실제 실행)</h2><table><tr><th></th><th>종류</th><th>질문</th><th>결과</th><th>어디서</th></tr>"
        + (red or "<tr><td colspan=5>04_redteam.py를 먼저 돌린다</td></tr>")
        + "</table>"
        + f"<h2>⑥ 비용 상한 — 낮추면 몇 문항이 멈추나 (지금 $0.05 · 최고 ${co['max']:.4f})</h2>"
        + f"<table><tr><th>상한</th><th>멈출 문항</th><th>그중 정답이던 것</th></tr>{caps}</table>",
    )


if __name__ == "__main__":
    serve(build(), 8838)
