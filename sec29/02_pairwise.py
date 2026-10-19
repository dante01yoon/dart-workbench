"""29편 ② 쌍 비교와 위치 바꾸기 — 답 두 개 중 나은 쪽을 고르게 하고, 순서를 바꿔 한 번 더 묻는다.

정답을 아는 쌍만 만든다(26편 답 6개 × 3종류):
- 빠짐: 원래 답 vs 정답 항목이 든 문장 하나를 뺀 답(코드 채점기로 원래 통과 · 뺀 답 실패를 확인) → 원래 답이 나아야 한다
- 같은 답: 똑같은 답 두 개 → 무승부여야 한다(한쪽을 고르면 위치가 판정을 바꾼 것)
- 장황: 원래 답 vs 같은 답 + 새 정보 없는 출처 없는 문장 3개 → 원래 답 또는 무승부(긴 쪽을 고르면 장황함 편향)
사용: uv run python sec29/02_pairwise.py → data/pair29.json · http://127.0.0.1:8836  (--show: 저장된 결과로 화면만)
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor

from judge import ROOT, TRACES, answer, ask, evidence, grade

sys.path.insert(0, str(ROOT / "sec23"))
from page import page, serve

BASES = ["n16", "n18", "n20", "q36", "q35", "n22"]
FILLER = [
    "이 내용은 회사의 사업보고서와 재무 자료를 바탕으로 정리한 것입니다.",
    "투자자와 이해관계자가 회사의 현황을 이해하는 데 중요한 정보입니다.",
    "앞으로의 실적과 사업 환경 변화도 함께 지켜볼 필요가 있습니다.",
]
PAIR = """너는 공시 리서치 답 두 개를 비교하는 판사다. 루브릭(채점 기준표)으로 본다:
핵심 값이 공시와 같은가 · 묻는 항목을 빠짐없이 답했나 · 문장마다 출처가 있나 · 근거에 없는 내용을 지어내지 않았나.
[질문] {q}
[근거]
{ev}
[답 1]
{a1}
[답 2]
{a2}
먼저 이유를 한두 문장으로 쓰고, 그다음 더 나은 답을 골라라. 둘이 같은 수준이면 "tie". JSON 하나로: {{"reason": "...", "winner": "1"}}"""


def text(rep):
    return " ".join(s["sentence"] for s in rep)


def drop_key(x):
    """정답 항목이 든 문장 하나를 빼서 코드 채점기가 실패하게 되는 답을 만든다."""
    rep = x["report"]
    for i in range(len(rep)):
        cut = rep[:i] + rep[i + 1 :]
        if not grade(x["keys"], text(cut), x["type"], qid=x["id"]):
            return cut
    raise ValueError(x["id"])


def pairs():
    out = []
    for qid in BASES:
        x = TRACES[qid]
        assert grade(x["keys"], text(x["report"]), x["type"], qid=qid), qid
        pad = x["report"] + [{"sentence": s, "cites": []} for s in FILLER]
        for kind, good, other in (("빠짐", x["report"], drop_key(x)), ("같은 답", x["report"], x["report"]),
                                  ("장황", x["report"], pad)):  # fmt: skip
            out.append({"id": qid, "kind": kind, "good": good, "other": other})
    return out


def judge_pair(p):
    x = TRACES[p["id"]]
    res = []
    for order in ("good_first", "other_first"):
        a1, a2 = (p["good"], p["other"]) if order == "good_first" else (p["other"], p["good"])
        v, c = ask(PAIR.format(q=x["q"], ev=evidence(x), a1=answer(a1), a2=answer(a2)))
        w = str(v.get("winner", "?"))
        pick = {"tie": "무승부", "1": "앞 답", "2": "뒤 답"}.get(w, "?")
        if p["kind"] != "같은 답" and w in ("1", "2"):
            pick = (
                "원래 답"
                if (w == "1") == (order == "good_first")
                else ("뺀 답" if p["kind"] == "빠짐" else "긴 답")
            )
        res.append({"order": order, "pick": pick, "why": v.get("reason", ""), "cost": c})
    return {"id": p["id"], "kind": p["kind"], "runs": res}


def summary(res):
    s = {}
    for kind in ("빠짐", "같은 답", "장황"):
        rs = [r for r in res if r["kind"] == kind]
        flip = sum(r["runs"][0]["pick"] != r["runs"][1]["pick"] for r in rs)
        picks = [run["pick"] for r in rs for run in r["runs"]]
        s[kind] = {"n": len(rs), "flip": flip, "picks": {k: picks.count(k) for k in dict.fromkeys(picks)}}
    return s


def html(res, s, calls, cost):
    trs = ""
    for r in res:
        a, b = r["runs"]
        cls = "ok" if a["pick"] == b["pick"] else "no"
        trs += (
            f"<tr><td class=num>{r['id']}</td><td>{r['kind']}</td><td class=num>{a['pick']}</td><td class=num>{b['pick']}</td>"
            f"<td class={cls}>{'같음' if a['pick'] == b['pick'] else '갈림'}</td></tr>"
        )
    head = " · ".join(f"{k} {v['flip']}/{v['n']}" for k, v in s.items())
    picks = "<br>".join(f"{k}: " + ", ".join(f"{p} {n}" for p, n in v["picks"].items()) for k, v in s.items())
    return page(
        "쌍 비교 · 위치 바꾸기",
        "<h1>쌍 비교 — 순서를 바꿔 한 번 더 묻기</h1>"
        f"<p class=sub>deepseek-v4-flash · 쌍 {len(res)}개 × 순서 2 = 호출 {calls}번 · ${cost:.4f} · 모두 정답을 아는 쌍</p>"
        f"<h2>순서를 바꾸면 판정이 갈린 쌍: {head}</h2><p class=sub>{picks}</p>"
        f"<table><tr><th></th><th>쌍</th><th>원래 답 먼저</th><th>바꾼 순서</th><th></th></tr>{trs}</table>",
    )


if __name__ == "__main__":
    out = ROOT / "data" / "pair29.json"
    if "--show" in sys.argv:  # 저장된 결과로 화면만(모델 호출 없음)
        d = json.loads(out.read_text())
        serve(html(d["res"], summary(d["res"]), d["calls"], d["cost"]), 8836)
        sys.exit()
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(judge_pair, pairs()))
    calls, cost = 2 * len(res), sum(run["cost"] for r in res for run in r["runs"])
    out.write_text(json.dumps({"res": res, "calls": calls, "cost": cost}, ensure_ascii=False, indent=1))
    for r in res:
        print(
            f"  {r['id']} {r['kind']:5s} 원래 답 먼저 → {r['runs'][0]['pick']:5s} 바꾼 순서 → {r['runs'][1]['pick']}"
        )
    for k, v in summary(res).items():
        print(
            f"{k}: 순서 바꾸면 갈림 {v['flip']}/{v['n']} · "
            + ", ".join(f"{p} {n}" for p, n in v["picks"].items())
        )
    print(f"호출 {calls}번 · ${cost:.4f}")
    serve(html(res, summary(res), calls, cost), 8836)
