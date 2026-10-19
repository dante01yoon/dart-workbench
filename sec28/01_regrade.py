"""28편 ① 채점기 다시 채점 — 같은 답을 채점기 v1(13편) · v2(22편 정정) · v3(오늘)로 채점해 무엇이 바뀌는지 본다. 모델 호출 없음.

답 세 묶음(모두 저장된 실제 답):
- 22편 처음 버전 20문항(data/final_eval.json) — 15/20으로 발표했다가 18/20으로 정정한 그 답
- 10/18 처음 버전 세 번 돌리기 60개(data/repeat3_1018.json) — 사람이 읽고 거절로 본 답 3개를 v2가 놓쳤다
- 26편 개발 문항 53개(data/traces26.jsonl) — 사람 메모(data/memos26.json)와 맞는지 본다
사용: uv run python sec28/01_regrade.py → http://127.0.0.1:8831
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "sec23"))
sys.path.insert(0, str(HERE))
import grader
from page import page, serve

KEYS = json.loads((ROOT / "eval" / "answer_keys.json").read_text())
TYPES = {
    json.loads(line)["id"]: json.loads(line)["type"] for line in (ROOT / "eval" / "questions.jsonl").open()
}
AGENT = {"계획", "공시 검색", "재무 조회", "뉴스 검색", "작성", "심판"}


def report(x):
    return " ".join(s["sentence"] for s in x["report"]) + " " + " ".join(e["claim"] for e in x["evidence"])


def sets():
    first = json.loads((ROOT / "data" / "final_eval.json").read_text())["first"]
    rep = json.loads((ROOT / "data" / "repeat3_1018.json").read_text())
    t26 = [json.loads(line) for line in (ROOT / "data" / "traces26.jsonl").open()]
    memos = json.loads((ROOT / "data" / "memos26.json").read_text())
    rows = [
        ("22편 처음 버전", x["id"], "", KEYS[x["id"]], TYPES[x["id"]], x["answer"], False, None)
        for x in first
    ]
    rows += [
        ("10/18 세 번", x["id"], x["round"], KEYS[x["id"]], TYPES[x["id"]], x["answer"], False, None)
        for x in rep
    ]
    for x in t26:  # 사람 판정: 메모가 에이전트 단계를 가리키고, 정답 자체가 틀린 문항만 실패(q45는 정답은 맞고 덧붙인 문장 문제)
        m = memos.get(x["id"], {})
        human = not (m.get("stage") in AGENT and x["id"] != "q45")
        rows.append(("26편 개발", x["id"], "", x["keys"], x["type"], report(x), x["refused"], human))
    return rows


def run():
    out = []
    for name, qid, rnd, keys, qtype, text, refused, human in sets():
        v = [grader.grade(keys, text, qtype, refused, version=k, qid=qid) for k in (1, 2, 3)]
        out.append({"set": name, "id": qid, "round": rnd, "v": v, "human": human, "text": text})
    return out


def html(out):
    names = ["22편 처음 버전", "10/18 세 번", "26편 개발"]
    trs = "".join(
        f"<tr><td>{n}</td>"
        + "".join(
            f"<td class=num>{sum(r['v'][k] for r in out if r['set'] == n)}/{sum(r['set'] == n for r in out)}</td>"
            for k in (0, 1, 2)
        )
        + "</tr>"
        for n in names
    )
    diff = "".join(
        f"<tr><td>{r['set']}</td><td class=num>{r['id']} {r['round']}</td><td class=num>{'✅' if r['v'][1] else '❌'} → {'✅' if r['v'][2] else '❌'}</td>"
        f"<td style='font-size:18px'>{r['text'][:150]}…</td></tr>"
        for r in out
        if r["v"][1] != r["v"][2]
    )
    c = [r for r in out if r["set"] == "26편 개발"]
    agree = [sum(r["v"][k] == r["human"] for r in c) for k in (1, 2)]
    return page(
        "채점기 다시 채점",
        "<h1>같은 답, 채점기만 바꿔서</h1><p class=sub>v1 13편 · v2 22편 정정(10/18) · v3 오늘(거절 문구 · 근거 없음 공시 기준 · 정답 키 3개)</p>"
        f"<table><tr><th>답 묶음</th><th>v1</th><th>v2</th><th>v3</th></tr>{trs}</table>"
        f"<p class=sub>26편 53문항 사람 메모와 일치: v2 {agree[0]}/{len(c)} → v3 {agree[1]}/{len(c)}</p>"
        f"<h2>v2 → v3에서 바뀐 줄</h2><table><tr><th>묶음</th><th>문항</th><th>판정</th><th>답 앞부분</th></tr>{diff}</table>",
    )


if __name__ == "__main__":
    out = run()
    for n in ("22편 처음 버전", "10/18 세 번", "26편 개발"):
        rs = [r for r in out if r["set"] == n]
        print(
            f"{n:10s} v1 {sum(r['v'][0] for r in rs):2d} · v2 {sum(r['v'][1] for r in rs):2d} · v3 {sum(r['v'][2] for r in rs):2d}  / {len(rs)}"
        )
    for r in out:
        if r["v"][1] != r["v"][2]:
            print(
                f"  바뀜 {r['set']} {r['id']} {r['round']}: {'✅' if r['v'][1] else '❌'} → {'✅' if r['v'][2] else '❌'}"
            )
    c = [r for r in out if r["set"] == "26편 개발"]
    print(
        f"26편 사람 메모와 일치: v2 {sum(r['v'][1] == r['human'] for r in c)}/{len(c)} → v3 {sum(r['v'][2] == r['human'] for r in c)}/{len(c)}"
    )
    serve(html(out), 8831)
