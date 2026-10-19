"""30편 ② 판사 검증 리포트 — 사람 라벨(data/labels30.json)과 이미 저장된 판정을 맞대 본다. 모델 호출 없음.

A. R2 빠짐없이 14문항: 29편 판사(27편 지시문 · 판사 v2) · 코드 채점 vs 사람 R2 라벨
B. 전체 통과/실패 53문항: 22편 채점기 v2 · 28편 채점기 v3 · "항상 통과" vs 사람 전체 라벨 → 일치율이 왜 속이나
C. R6 지어내지 않음: 29편 판사 — 일부러 넣은 문장 8개(정답이 실패로 정해짐)와 원본 8개(사람 R6 라벨은 라벨링 페이지에서)
사용: uv run python sec30/02_validate.py → http://127.0.0.1:8841  (--no-serve: 출력만)
"""

import importlib
import json
import sys
from math import isnan
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for d in ("sec23", "sec28"):
    sys.path.insert(0, str(ROOT / d))
import grader  # 28편 코드 채점기(v1 · v2 · v3)
from labels import DATA, TRACES, load
from metrics import confusion, summary
from page import page, serve

RG = importlib.import_module("01_regrade")  # 28편: 채점기에 넘기는 글(report)
J29 = json.loads((DATA / "judge29.json").read_text())


def r2():
    human = load("R2")
    judges = {
        "27편 지시문": {r["id"]: r["v1"] for r in J29["a"]},
        "판사 v2": {r["id"]: r["v2"] for r in J29["a"]},
        "코드 R2": {r["id"]: r["code"] for r in J29["a"]},
    }
    return human, judges


def overall(explicit_only=False):
    human = load("전체", explicit_only)
    xs = [TRACES[i] for i in human]
    g = lambda v: {
        x["id"]: grader.grade(x["keys"], RG.report(x), x["type"], x["refused"], version=v, qid=x["id"])
        for x in xs
    }
    return human, {"채점기 v2(22편)": g(2), "채점기 v3(28편)": g(3), "항상 통과": {i: True for i in human},
                   "항상 실패": {i: False for i in human}}  # fmt: skip


def r6():
    """넣은 문장 8개는 실패로 정해져 있다(합성 라벨). 원본 8개의 R6 라벨은 라벨링 페이지에서 단 것만(시연 제외)."""
    new = DATA / "labels30_new.jsonl"
    rows = [json.loads(line) for line in new.open()] if new.exists() else []
    mine = {
        r["id"]: r["label"] == "통과"
        for r in rows
        if r["criterion"] == "R6" and r["labeler"] != "시연" and r["label"] != "보류"
    }
    human = {f"{r['id']}+": False for r in J29["b"] if r["fake"]} | {r["id"]: mine[r["id"]] for r in J29["b"] if not r["fake"] and r["id"] in mine}  # fmt: skip
    judge = {(r["id"] + "+" if r["fake"] else r["id"]): r["one"] for r in J29["b"]}
    flagged = [r["id"] for r in J29["b"] if not r["fake"] and r["one"] is False]
    return human, {"판사 v2 R6": judge}, flagged


def pct(v):
    return "  -  " if isnan(v) else f"{v * 100:5.1f}%"


def kap(v):
    return "  - " if isnan(v) else f"{v:+.2f}"


def line(name, s):
    return (f"  {name:14s} TP {s['TP']:2d} FN {s['FN']:2d} FP {s['FP']:2d} TN {s['TN']:2d} │ 일치 {pct(s['agree'])}"
            f" · TPR {pct(s['tpr'])} · TNR {pct(s['tnr'])} · kappa {kap(s['kappa'])}")  # fmt: skip


def block(human, judges):
    return {k: summary(confusion(human, j)) for k, j in judges.items()}


def matrix(name, s):
    cell = lambda k, cls: f"<td class='m {cls}'><b>{s[k]}</b><small>{k}</small></td>"
    ci = lambda lo_hi: f"{lo_hi[0] * 100:.0f}~{lo_hi[1] * 100:.0f}%" if not isnan(lo_hi[0]) else "-"
    return (f"<div class=card><b>{name}</b><table class=cm><tr><th></th><th>판정 실패</th><th>판정 통과</th></tr>"
            f"<tr><th>사람 실패</th>{cell('TP', 'hit')}{cell('FN', 'miss')}</tr>"
            f"<tr><th>사람 통과</th>{cell('FP', 'miss')}{cell('TN', 'hit')}</tr></table>"
            f"<p class=num>일치 {pct(s['agree'])} · kappa {kap(s['kappa'])}<br>TPR {pct(s['tpr'])} ({ci(s['tpr_ci'])})"
            f"<br>TNR {pct(s['tnr'])} ({ci(s['tnr_ci'])})</p></div>")  # fmt: skip


CSS = """<style>.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.cm{width:auto;margin:8px 0}
.cm td.m{width:118px;text-align:center;font-size:30px}.cm td.m small{display:block;font-size:15px;color:#9aa0aa}
.cm td.hit{background:#1f3326}.cm td.miss{background:#3a2323}.card p{margin:6px 0 0;font-size:19px}</style>"""


def html(A, B, B14, C, flagged, nA, nB):
    sec = lambda res: "<div class=cards>" + "".join(matrix(k, s) for k, s in res.items()) + "</div>"
    return page(
        "판사 검증",
        CSS + "<h1>판사 검증 리포트 — 사람 라벨 vs 판사</h1>"
        f"<p class=sub>사람 라벨: 라벨러 1명(단테 검토 10/19) · 양성 = 실패 · 괄호는 윌슨 95% 구간 · 모델 호출 0</p>"
        f"<h2>A. R2 빠짐없이 — {nA}</h2>{sec(A)}"
        f"<p class=sub>판사 v2는 n07을 보고 고친 지시문(29편)이라 이 14개는 dev 성적이다. 손대지 않은 test 라벨은 아직 없다.</p>"
        f"<h2>B. 전체 통과/실패 — {nB}</h2>{sec(B)}"
        f"<p class=sub>채점기 v3는 이 라벨을 보고 고쳤다(28편) → 100%는 dev 성적. "
        f"메모로 단 14개만 보면(실패 12 · 통과 2): 항상 실패 일치 {pct(B14['항상 실패']['agree'])} · kappa {B14['항상 실패']['kappa']:+.2f}</p>"
        f"<h2>C. R6 지어내지 않음 — 넣은 문장 8개(합성 라벨) + 사람이 단 원본</h2>{sec(C)}"
        f"<p class=sub>판사가 원본에서 '아니오'라고 한 {len(flagged)}개({' · '.join(flagged)})는 사람 R6 라벨이 필요하다 → 라벨링 페이지(8840)</p>",
    )


if __name__ == "__main__":
    hA, jA = r2()
    hB, jB = overall()
    hB14, jB14 = overall(explicit_only=True)
    hC, jC, flagged = r6()
    A, B, B14, C = block(hA, jA), block(hB, jB), block(hB14, jB14), block(hC, jC)
    nf = lambda h: sum(not v for v in h.values())
    nA = f"{len(hA)}문항 · 사람 실패 {nf(hA)} · 통과 {len(hA) - nf(hA)} (메모 6 + 암묵 통과 8)"
    nB = f"{len(hB)}문항 · 사람 실패 {nf(hB)} · 통과 {len(hB) - nf(hB)} (메모 14 + 암묵 통과 39)"
    print(f"A. R2 빠짐없이 — {nA}")
    for k, s in A.items():
        print(line(k, s))
    print(f"B. 전체 통과/실패 — {nB}")
    for k, s in B.items():
        print(line(k, s))
    print(
        f"   메모로 단 14개만(실패 12 · 통과 2): 항상 실패 일치 {pct(B14['항상 실패']['agree'])} · kappa {B14['항상 실패']['kappa']:+.2f}"
    )
    print(f"C. R6 — 넣은 문장 8개 + 사람이 단 원본 {len(hC) - 8}개")
    for k, s in C.items():
        print(line(k, s))
    print(f"   원본에서 판사 '아니오' {len(flagged)}개({' · '.join(flagged)}): 사람 R6 라벨 필요")
    s = A["판사 v2"]
    print(
        f"주의: 판사 v2 TPR {s['TP']}/{s['TP'] + s['FN']}의 95% 구간 {s['tpr_ci'][0] * 100:.0f}~100% — 라벨이 적다(31편)"
    )
    if "--no-serve" not in sys.argv:
        serve(html(A, B, B14, C, flagged, nA, nB), 8841)
