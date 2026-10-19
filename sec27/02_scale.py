"""27편 ② 1~5점 vs 예/아니오 — 같은 답을 같은 모델에게 다섯 번씩 채점시켜 흔들림을 본다.

- 답: 26편 실행 기록에서 고른 3개(빠짐없이 답한 것 하나, 일부만 답한 것 둘).
- 1~5점: "이 답의 품질을 1~5점으로". 예/아니오: 루브릭 R2 "질문이 묻는 항목을 모두 답했나?"
- 모델 deepseek-v4-flash, 기본 설정(temperature 미지정). 판사를 제대로 만드는 건 29편, 오늘은 척도만 비교한다.
사용: uv run python sec27/02_scale.py → data/scale27.json · http://127.0.0.1:8834  (--show: 저장된 결과로 화면만)
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sec23"))
sys.path.insert(0, str(ROOT / "sec09"))
from context import chat  # 9편 모델 호출(OpenRouter)
from page import page, serve

PICK = ["n16", "n15", "n07"]  # 두 회사 비교(빠짐없음) · 사업 부문 일부 · 등기임원 4/9
N = 5
TRACES = {x["id"]: x for x in (json.loads(line) for line in (ROOT / "data" / "traces26.jsonl").open())}
LIKERT = '[질문]에 대한 [답]의 품질을 1~5점으로 매겨라. 숫자 하나만 JSON으로: {"score": 3}'
BINARY = '[질문]이 묻는 항목을 [답]이 모두 답했나? 예/아니오 하나만 JSON으로: {"pass": true}'


def ask(args):
    kind, qid = args
    x = TRACES[qid]
    answer = " ".join(s["sentence"] for s in x["report"])
    raw, u = chat(
        f"{LIKERT if kind == 'likert' else BINARY}\n\n[질문] {x['q']}\n[답] {answer}", max_tokens=6000
    )
    try:
        v = json.loads(raw[raw.index("{") : raw.rindex("}") + 1])
        v = v["score"] if kind == "likert" else ("예" if v["pass"] else "아니오")
    except (ValueError, KeyError):
        v = "?"
    return {"kind": kind, "id": qid, "value": v, "cost": float(u.get("cost") or 0)}


def html(res):
    trs = ""
    for qid in PICK:
        lk = [r["value"] for r in res if r["id"] == qid and r["kind"] == "likert"]
        bn = [r["value"] for r in res if r["id"] == qid and r["kind"] == "binary"]
        trs += (
            f"<tr><td>{qid} {TRACES[qid]['q']}</td><td class=num>{' · '.join(map(str, lk))}</td>"
            f"<td class=num>{len(set(lk))}가지</td><td class=num>{' · '.join(bn)}</td><td class=num>{len(set(bn))}가지</td></tr>"
        )
    return page(
        "1~5점 vs 예/아니오",
        f"<h1>같은 답 · 같은 모델 · {N}번씩</h1><p class=sub>deepseek-v4-flash · 예/아니오 기준 = 루브릭 R2 빠짐없이</p>"
        f"<table><tr><th>답</th><th>1~5점</th><th>나온 값</th><th>예/아니오(R2)</th><th>나온 값</th></tr>{trs}</table>",
    )


if __name__ == "__main__":
    if "--show" in sys.argv:  # 저장된 결과로 화면만(모델 호출 없음)
        serve(html(json.loads((ROOT / "data" / "scale27.json").read_text())), 8834)
        sys.exit()
    jobs = [(k, q) for q in PICK for k in ("likert", "binary") for _ in range(N)]
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(ask, jobs))
    (ROOT / "data" / "scale27.json").write_text(json.dumps(res, ensure_ascii=False))
    for qid in PICK:
        lk = [r["value"] for r in res if r["id"] == qid and r["kind"] == "likert"]
        bn = [r["value"] for r in res if r["id"] == qid and r["kind"] == "binary"]
        print(f"{qid}  1~5점: {' '.join(map(str, lk))}   예/아니오: {' '.join(bn)}")
    print(f"호출 {len(res)}번 · ${sum(r['cost'] for r in res):.4f}")
    serve(html(res), 8834)
