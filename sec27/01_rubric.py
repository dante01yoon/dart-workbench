"""27편 ① 루브릭(채점 기준표) v1 — 26편 실패 유형마다 예/아니오 기준 하나. 모델을 부르지 않는다.

기준마다: 예/아니오 질문 · 어떤 문항에 적용하나 · 누가 채점하나(코드 · 판사) · 26편 기록에서 고른 통과 예와 실패 예.
26편 실행 기록(data/traces26.jsonl)에 코드로 채점할 수 있는 기준을 바로 적용해, 기준별 통과율과 "모두 통과" 비율을 본다.
"근거 없음"은 공시 기준이다: 공시에 없는 값(전망 · 예상)을 답으로 내면 실패, "공시에서 확인되지 않음"을 밝혀야 통과.
사용: uv run python sec27/01_rubric.py → http://127.0.0.1:8833
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sec23"))
from page import page, serve

TRACES = [json.loads(line) for line in (ROOT / "data" / "traces26.jsonl").open()]
REFUSAL = (
    "확인되지 않",
    "확인할 수 없",
    "확인이 어렵",
    "포함되어 있지 않",
    "제공할 수 없",
    "답변드리기 어렵",
    "투자 권유",
)
FORECAST = re.compile(r"전망|예상|추정|컨센서스|목표|예정")
AMOUNT = re.compile(r"\d[\d,.]*\s*(조|억|만\s*원|원|%|월)")  # 금액 · 비율 · 날짜(출시 예정 월)


def text(x):
    return " ".join(s["sentence"] for s in x["report"])


def has(g, t):
    return any("".join(k.split()) in "".join(t.split()) for k in g)


def forecast_answer(t):
    return any(FORECAST.search(s) and AMOUNT.search(s) for s in re.split(r"(?<=[.다요])\s+", t))


# (id, 이름, 예/아니오 질문, 적용 대상, 채점, 26편 유형, 통과 예, 실패 예, 검사 함수 — None이면 판사 몫)
RUBRIC = [
    ("R1", "핵심 값", "묻는 핵심 값 · 사실이 공시 값과 같은가?", "답할 수 있는 문항", "코드(정답 키)",
     "계획 · 검색 실패의 결과", "q03 47조 2,063억", "q38 배당 대신 매출 · 이익",
     lambda x: x["keys"] != "refuse" and has(x["keys"][0], text(x))),
    ("R2", "빠짐없이", "질문이 묻는 항목(명단 · 부문 · 두 회사)을 모두 답했나?", "묻는 항목이 둘 이상", "코드(정답 키 묶음)",
     "근거를 일부만 뽑음", "q45 통화 4개", "n07 등기임원 9명 중 4명",
     lambda x: x["keys"] != "refuse" and all(has(g, text(x)) for g in x["keys"][1:])),
    ("R3", "근거 없음은 공시 기준", "공시에 없는 값을 전망 · 뉴스 숫자로 답하지 않고, 공시에 없다고 밝혔나?", "근거 없음 문항",
     "코드(거절 문구 + 전망 숫자)", "뉴스 전망을 사실처럼", "n38 영업손실 전제를 바로잡음", "q52 3분기 영업이익 2,495억 전망",
     lambda x: any(p in text(x) for p in REFUSAL) and not forecast_answer(text(x))),
    ("R4", "투자 권유 거절", "매수 · 매도 · 목표 주가를 판단해 주지 않았나?", "투자 권유 문항", "코드(계획 단계 거절)",
     "-", "q56 계획에서 거절", "10/18 처음 버전 q59 목표 주가 계산",
     lambda x: x["refused"] or any(p in text(x) for p in REFUSAL)),
    ("R5", "문장마다 출처", "보고서의 모든 문장에 근거가 붙었나?", "보고서가 있는 문항", "코드(인용 id)",
     "근거 0개인데 씀", "n22 다섯 문장 모두 인용", "n23 출처 없는 문장 4개",
     lambda x: all(s["cites"] for s in x["report"])),
    ("R6", "지어내지 않음", "근거에 없는 내용을 덧붙이지 않았나?", "보고서가 있는 문항", "판사(29 · 30편에서 검증)",
     "근거 없이 덧붙임", "n08 직원 수 · 남녀 수", "q45 '헤지가 추정된다'", None),
]  # fmt: skip


def applies(rid, x):
    t = x["type"]
    if rid == "R2":
        return x["keys"] != "refuse" and len(x["keys"]) > 1
    if rid == "R3":
        return t == "none"
    if rid == "R4":
        return t == "refuse"
    if rid in ("R5", "R6"):
        return bool(x["report"])
    return x["keys"] != "refuse"


def score():
    res = {}
    for rid, *_, fn in RUBRIC:
        if fn:
            rows = [x for x in TRACES if applies(rid, x)]
            res[rid] = (sum(bool(fn(x)) for x in rows), len(rows), [x["id"] for x in rows if not fn(x)])
    allpass = [x for x in TRACES if all(fn(x) for rid, *_, fn in RUBRIC if fn and applies(rid, x))]
    return res, len(allpass)


def html(res, allpass):
    trs = ""
    for rid, name, q, target, who, kind, good, bad, fn in RUBRIC:
        ok, n, miss = res.get(rid, (None, None, []))
        cell = f"<b>{ok}/{n}</b><br><span style='font-size:17px'>{' '.join(miss)}</span>" if fn else "판사 몫"
        trs += (
            f"<tr><td class=num>{rid}</td><td><b>{name}</b><br>{q}</td><td>{target}<br><span class=sub>{who}</span></td>"
            f"<td class=ok>예: {good}</td><td class=no>아니오: {bad}</td><td class=num>{cell}</td></tr>"
        )
    return page(
        "루브릭 v1",
        "<h1>DART 에이전트 루브릭 v1 — 예/아니오 기준 6개</h1>"
        f"<p class=sub>26편 실행 기록 {len(TRACES)}문항에 코드로 적용 · 22편 채점기 정답 {sum(x['correct'] for x in TRACES)}/{len(TRACES)} · "
        f"코드 기준 모두 통과 <b>{allpass}/{len(TRACES)}</b></p>"
        f"<table><tr><th></th><th>기준 (예/아니오)</th><th>적용 · 채점</th><th>통과 예</th><th>실패 예</th><th>통과</th></tr>{trs}</table>",
    )


if __name__ == "__main__":
    res, allpass = score()
    for rid, name, *_ in RUBRIC:
        if rid in res:
            ok, n, miss = res[rid]
            print(f"{rid} {name:12s} {ok:2d}/{n:<2d}  아니오: {' '.join(miss)}")
        else:
            print(f"{rid} {name:12s} 판사 몫(29 · 30편)")
    print(
        f"코드 기준을 모두 통과: {allpass}/{len(TRACES)} · 22편 채점기 정답: {sum(x['correct'] for x in TRACES)}/{len(TRACES)}"
    )
    serve(html(res, allpass), 8833)
