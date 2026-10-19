"""25편 ③ 시험지 v2 — 개발(dev)과 held-out을 나누고, 새는 문항이 없는지 검사한 뒤 화면으로 본다. API를 부르지 않는다.

나누는 규칙 하나: 개발하면서 이미 돌려 보고 고친 문항은 개발용이다.
- 개발: 13~22편 내내 보던 20문항 + 실행 기록에서 온 질문(16편 과제 1은 이 질문들로 도구 설명을 고쳤다)
- held-out: 아무도 돌려 본 적 없는 문항(기록의 모양만 빌린 새 문항 + 함정 + 은행에서 아직 안 쓴 문항)
- 뺌: 24편에서 돌려 본 20문항(개발 20문항과 같은 틀의 템플릿 → 대표성을 위해 v2에 넣지 않는다)
새는 문항 검사: held-out 문항이 개발 문항과 같은 질문(회사 · 연도 · 항목이 같거나, 회사와 정답 키가 같음)이고
기대하는 행동(답 · 거절)도 같으면 개발로 옮긴다.
사용: uv run python sec25/03_build_set.py → eval/questions_v2.jsonl · http://127.0.0.1:8827
"""

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "sec23"))
from page import page, serve

spec = importlib.util.spec_from_file_location("collect", HERE / "01_collect.py")
collect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect)  # same(): 회사 · 연도 · 항목이 같은가

BANK = {json.loads(line)["id"]: json.loads(line) for line in (ROOT / "eval" / "questions.jsonl").open()}
KEYS = json.loads((ROOT / "eval" / "answer_keys.json").read_text())
SEEN13 = ["q01", "q03", "q06", "q09", "q28", "q30", "q31", "q36", "q37", "q40"]
SEEN13 += ["q44", "q45", "q47", "q49", "q15", "q17", "q51", "q54", "q56", "q59"]  # 13~22편
SEEN24 = ["q02", "q04", "q05", "q07", "q29", "q32", "q33", "q38", "q39", "q41"]
SEEN24 += ["q46", "q48", "q50", "q13", "q14", "q16", "q52", "q53", "q57", "q58"]  # 24편 — v2에 넣지 않음
# 은행에서 아직 안 쓴 문항: held-out에 전년 대비 · 회사 비교 · 근거 없음 유형을 채운다
UNUSED = ["q34", "q35", "q42", "q43", "q55"]


def twin(a, b):
    """같은 자료를 묻고(회사 · 연도 · 항목, 또는 회사와 정답 키) 같은 행동(답하기 · 거절하기)을 기대하면 같은 질문이다."""
    same_key = a["keys"] == b["keys"] != "refuse" and collect.slots(a["q"])[0] == collect.slots(b["q"])[0]
    return (collect.same(a["q"], b["q"]) or same_key) and (a["keys"] == "refuse") == (b["keys"] == "refuse")


def last_runs():
    """기록에 남은 마지막 실행(정답 · 초 · 비용) — 트레이스가 시험지 옆에 붙어 있으면 어디가 느리고 비싼지 바로 보인다."""
    runs = {x["id"]: x for x in json.loads((DATA / "final_eval.json").read_text())["now"]}
    if (DATA / "heldout24.json").exists():
        h = json.loads((DATA / "heldout24.json").read_text())
        runs.update({x["id"]: x for x in h["dev"] + h["new"]})
    return runs


def build():
    rows = [{"id": i, "q": BANK[i]["q"], "type": BANK[i]["type"], "source": "13편 시험지", "split": "dev", "keys": KEYS[i]}
            for i in SEEN13]  # fmt: skip
    new, dropped, twins = [], [], []
    for g in json.loads((DATA / "sec25_gold.json").read_text()):
        if g["type"] == "drop":
            dropped.append(g)
        elif g["file"] and any(twin(g, n) for n in rows + new):
            twins.append(g["q"])  # 기록 속 질문이 이미 있는 질문을 다른 말로 한 것
        else:
            seen = g["file"] is not None  # 실행 기록에서 온 질문 = 개발하면서 이미 돌려 본 질문
            new.append(
                {"q": g["q"], "type": g["type"], "source": g["source"], "keys": g["keys"], "seen": seen}
            )
    new += [{"id": i, "q": BANK[i]["q"], "type": BANK[i]["type"], "source": "은행(아직 안 돌림)", "keys": KEYS[i], "seen": False}
            for i in UNUSED]  # fmt: skip
    for k, n in enumerate(new, 1):
        n.setdefault("id", f"n{k:02d}")
        n["split"] = "dev" if n.pop("seen") else "heldout"
    moved = []
    for n in [x for x in new if x["split"] == "heldout"]:
        hit = next((r for r in rows + new if r["split"] == "dev" and twin(n, r)), None)
        if hit:  # 개발 문항과 같은 질문 → held-out에 두면 샌다
            n["split"] = "dev"
            moved.append((n["q"], hit["id"]))
    return rows + new, dropped, twins, moved


def html(v2, dropped, twins, moved, runs):
    def table(split):
        trs = ""
        for r in [x for x in v2 if x["split"] == split]:
            run = runs.get(r["id"])
            last = (
                f"{'✅' if run['correct'] else '❌'} {run['seconds']:.0f}초 ${run['cost']:.4f}"
                if run
                else "-"
            )
            key = "거절해야 정답" if r["keys"] == "refuse" else " · ".join(g[0] for g in r["keys"])
            trs += f"<tr><td class=num>{r['id']}</td><td>{r['q']}</td><td>{r['type']}</td><td>{r['source']}</td><td>{key}</td><td class=num>{last}</td></tr>"
        return f"<table><tr><th>id</th><th>질문</th><th>유형</th><th>출처</th><th>정답 키</th><th>마지막 실행</th></tr>{trs}</table>"

    n = Counter(r["split"] for r in v2)
    chips = "".join(
        f"<span class=tag>{k} {v}</span>" for k, v in Counter(r["type"] for r in v2).most_common()
    )
    out = "".join(f"<span class=tag>{d['q']} — {d['why']}</span>" for d in dropped)
    out += "".join(f"<span class=tag>{q} — 같은 질문(정답 키 같음)</span>" for q in twins)
    out += "".join(f"<span class=tag>{q} → 개발로 옮김({i}와 같은 질문)</span>" for q, i in moved)
    return page(
        "시험지 v2",
        f"<h1>시험지 v2 · {len(v2)}문항</h1>"
        f"<p class=sub>개발 {n['dev']} · held-out {n['heldout']} · 정답은 공시 API · 재무 API 값 · "
        f"24편 20문항은 개발과 같은 틀이라 넣지 않음</p>"
        f"<div>{chips}</div><h2>뺀 것 · 옮긴 것</h2><div>{out}</div>"
        f"<h2>held-out {n['heldout']} — 아직 아무도 안 돌림</h2>{table('heldout')}"
        f"<h2>개발 {n['dev']}</h2>{table('dev')}",
    )


if __name__ == "__main__":
    v2, dropped, twins, moved = build()
    for q, i in moved:
        print(f"새는 문항: {q} = {i} → 개발로 옮김")
    for q in twins:
        print(f"같은 질문: {q}")
    n = Counter(r["split"] for r in v2)
    print(f"시험지 v2 {len(v2)}문항 = 개발 {n['dev']} + held-out {n['heldout']}")
    print("유형:", dict(Counter(r["type"] for r in v2)))
    leaks = [
        (h["q"], d["id"])
        for h in v2
        if h["split"] == "heldout"
        for d in v2
        if d["split"] == "dev" and twin(h, d)
    ]
    print(f"검사: held-out ↔ 개발 같은 질문 {len(leaks)}개")
    with (ROOT / "eval" / "questions_v2.jsonl").open("w", encoding="utf-8") as f:
        for r in v2:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    serve(html(v2, dropped, twins, moved, last_runs()), 8827)
