"""29편 ① LLM 판사 — 27편 루브릭 기준을 판사로 채점하고, 정답을 아는 경우와만 대조한다.

A. R2 빠짐없이(14문항): 27편 지시문(v1, 기준 문장만) vs 판사 v2(통과 · 실패 예 + 정답 정보 + 이유 먼저).
   비교 대상은 코드 채점(27편 R2 — 정답 키가 공시에서 나온다). 사람 라벨과의 비교는 30편.
B. R6 지어내지 않음: 26편 깨끗한 답 8개 + 같은 답 끝에 근거에 없는 문장을 하나 일부러 넣은 8개.
   넣은 문장은 정답이 "아니오"로 정해져 있다. 기준 하나씩 판사 vs 기준 6개를 한 번에 묻는 판사.
사용: uv run python sec29/01_judge.py → data/judge29.json · http://127.0.0.1:8835  (--show: 저장된 결과로 화면만)
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor

from judge import RB, ROOT, TRACES, ask, prompt_all, prompt_v1, prompt_v2

sys.path.insert(0, str(ROOT / "sec23"))
from page import page, serve

# 근거에 없는 문장(인용은 있는 근거 id를 그대로 붙였다 — 출처가 붙어 있어도 지어낸 말)
FAKE = {
    "q01": ("이는 반도체 부문 영업이익이 전체의 70%를 차지한 결과입니다.", "e2"),
    "q09": ("영업이익 증가는 카카오톡 광고 매출이 30% 늘어난 덕분입니다.", "e2"),
    "q17": ("현대모비스는 2026년까지 지분을 25%로 늘릴 계획이라고 공시했다.", "e1"),
    "n02": ("카카오는 2026년에 본사를 경기도 성남시 판교로 옮길 예정입니다.", "e2"),
    "n10": ("감사인은 내부회계관리제도에서 중요한 취약점 2건도 지적했다.", "e1"),
    "n22": ("전체 직원의 평균 근속연수는 12.8년이다.", "e1"),
    "q49": ("포털비즈 매출은 2025년 4,200억 원으로 전년보다 8% 줄었습니다.", "e1"),
    "n18": ("카카오는 2026년 영업이익 1조 원을 목표로 제시했습니다.", "e2"),
}


def faked(qid):
    s, e = FAKE[qid]
    return TRACES[qid]["report"] + [{"sentence": s, "cites": [e]}]


def run_a(qid):
    x = TRACES[qid]
    v1, c1 = ask(prompt_v1(x, x["report"]))
    v2, c2 = ask(prompt_v2("R2", x, x["report"]))
    code = bool(RB.RUBRIC[1][-1](x))
    return {
        "id": qid,
        "code": code,
        "v1": v1.get("pass"),
        "v2": v2.get("pass"),
        "why": v2.get("reason", ""),
        "cost": c1 + c2,
    }


def run_b(job):
    qid, fake = job
    x, rep = TRACES[qid], faked(qid) if fake else TRACES[qid]["report"]
    one, c1 = ask(prompt_v2("R6", x, rep))
    allv, c2 = ask(prompt_all(x, rep))
    return {
        "id": qid,
        "fake": fake,
        "one": one.get("pass"),
        "all": allv.get("R6"),
        "why": one.get("reason", ""),
        "cost": c1 + c2,
    }


def yn(v):
    return {True: "<span class=ok>예</span>", False: "<span class=no>아니오</span>"}.get(v, "?")


def html(res):
    a, b = res["a"], res["b"]
    agree = lambda k: sum(r[k] == r["code"] for r in a)
    rows_a = "".join(
        f"<tr><td class=num>{r['id']}</td><td>{TRACES[r['id']]['q']}</td><td class=num>{yn(r['code'])}</td>"
        f"<td class=num>{yn(r['v1'])}</td><td class=num>{yn(r['v2'])}</td><td style='font-size:17px'>{r['why'][:90]}</td></tr>"
        for r in a
        if r["v1"] != r["code"] or r["v2"] != r["code"] or not r["code"]
    )
    caught = lambda k: sum(r[k] is False for r in b if r["fake"])
    flag = lambda k: sum(r[k] is False for r in b if not r["fake"])
    rows_b = "".join(
        f"<tr><td class=num>{r['id']}</td><td>{FAKE[r['id']][0]}</td><td class=num>{yn(r['one'])}</td>"
        f"<td class=num>{yn(r['all'])}</td><td style='font-size:17px'>{r['why'][:90]}</td></tr>"
        for r in b
        if r["fake"]
    )
    return page(
        "LLM 판사",
        "<h1>LLM 판사 v2 — 루브릭 기준 하나에 판사 하나</h1>"
        f"<p class=sub>deepseek-v4-flash · 호출 {res['calls']}번 · ${res['cost']:.4f} · 비교 대상은 코드 채점과 일부러 만든 답(사람 라벨은 30편)</p>"
        f"<h2>A. R2 빠짐없이 — 코드 채점과 같은 판정: 27편 지시문 {agree('v1')}/{len(a)} · 판사 v2 {agree('v2')}/{len(a)}</h2>"
        "<table><tr><th></th><th>질문</th><th>코드</th><th>27편 지시문</th><th>판사 v2</th><th>판사 v2 이유</th></tr>"
        f"{rows_a}</table>"
        f"<h2>B. R6 지어내지 않음 — 일부러 넣은 문장 8개 중 잡은 수: 기준 하나씩 {caught('one')}/8 · 한 번에 {caught('all')}/8</h2>"
        f"<p class=sub>넣기 전 원본 8개에 아니오: 기준 하나씩 {flag('one')} · 한 번에 {flag('all')}</p>"
        "<table><tr><th></th><th>넣은 문장</th><th>기준 하나씩</th><th>한 번에</th><th>이유(기준 하나씩)</th></tr>"
        f"{rows_b}</table>",
    )


if __name__ == "__main__":
    out = ROOT / "data" / "judge29.json"
    if "--show" in sys.argv:  # 저장된 결과로 화면만(모델 호출 없음)
        serve(html(json.loads(out.read_text())), 8835)
        sys.exit()
    ids = [x["id"] for x in TRACES.values() if RB.applies("R2", x)]
    with ThreadPoolExecutor(6) as ex:
        a = list(ex.map(run_a, ids))
        b = list(ex.map(run_b, [(q, f) for q in FAKE for f in (False, True)]))
    res = {"a": a, "b": b, "calls": 2 * (len(a) + len(b)), "cost": sum(r["cost"] for r in a + b)}
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print("A. R2 빠짐없이 (코드 · 27편 지시문 · 판사 v2)")
    for r in a:
        print(f"  {r['id']}  코드 {'예' if r['code'] else '아니오':3s} 27편 {r['v1']!s:5s} v2 {r['v2']!s:5s}")
    print(f"  코드와 같은 판정: 27편 지시문 {sum(r['v1'] == r['code'] for r in a)}/{len(a)}"
          f" · 판사 v2 {sum(r['v2'] == r['code'] for r in a)}/{len(a)}")  # fmt: skip
    one = sum(r["one"] is False for r in b if r["fake"])
    allv = sum(r["all"] is False for r in b if r["fake"])
    print(f"B. 넣은 문장 잡음: 기준 하나씩 {one}/8 · 한 번에 {allv}/8")
    print(f"   원본에 아니오: 기준 하나씩 {sum(r['one'] is False for r in b if not r['fake'])}/8"
          f" · 한 번에 {sum(r['all'] is False for r in b if not r['fake'])}/8")  # fmt: skip
    print(f"호출 {res['calls']}번 · ${res['cost']:.4f}")
    serve(html(res), 8835)
