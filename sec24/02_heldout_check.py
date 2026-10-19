"""24편 ② 우리 시험지로 하는 GSM1k식 검사 — 13~22편 내내 보며 고친 20문항(개발 세트)과,
같은 유형 비율로 고른 처음 보는 20문항(같은 60문항 은행에서 한 번도 안 쓴 문항)을 같은 날 같은 워크벤치로 돌려 비교한다.
점수가 크게 떨어지면 "시험지에 맞춰 고쳤다"(과적합) 신호다. 모델은 deepseek-v4-flash.
사용: uv run python sec24/02_heldout_check.py → data/heldout24.json · scorecard.jsonl 두 줄 · http://127.0.0.1:8826
      uv run python sec24/02_heldout_check.py --show → 저장된 결과로 화면만
"""

import importlib.util
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "sec23"))
from page import page, serve

spec = importlib.util.spec_from_file_location("final", ROOT / "sec22" / "01_final_scorecard.py")
final = importlib.util.module_from_spec(spec)
spec.loader.exec_module(final)  # 22편 run_now · grade · row (워크벤치 + 원격이 아닌 로컬 MCP)

DEV = final.IDS  # 13편부터 보던 20문항
# 처음 보는 20문항: 개발 세트와 같은 유형 비율로, 60문항 은행에서 한 번도 안 쓴 문항
NEW = ["q02", "q04", "q05", "q07", "q29", "q32", "q33", "q38", "q39", "q41"]  # fmt: skip
NEW += ["q46", "q48", "q50", "q13", "q14", "q16", "q52", "q53", "q57", "q58"]  # fmt: skip
TYPES = [("number", "숫자"), ("year_compare", "전년 대비"), ("cross_company", "회사 비교"), ("narrative", "서술"),
         ("fact", "사실"), ("none", "근거 없음"), ("refuse", "투자 권유")]  # fmt: skip


def grams(s):
    s = "".join(s.split())
    return {s[i : i + 3] for i in range(len(s) - 2)}


def nearest(qid):
    """처음 보는 문항과 가장 닮은 개발 문항(글자 3개 묶음 자카드) — 템플릿이 같아도 값이 다르면 외워서는 못 맞힌다."""
    g = grams(final.qs[qid]["q"])
    best = max(DEV, key=lambda d: len(g & grams(final.qs[d]["q"])) / len(g | grams(final.qs[d]["q"])))
    return best, round(len(g & grams(final.qs[best]["q"])) / len(g | grams(final.qs[best]["q"])), 2)


def by_type(res):
    return {t: (sum(x["correct"] for x in res if final.qs[x["id"]]["type"] == t),
                sum(final.qs[x["id"]]["type"] == t for x in res)) for t, _ in TYPES}  # fmt: skip


def then():
    """22편(10/17)에 같은 개발 20문항을 돌린 기록 — 같은 모델 이름이어도 날이 다르면 숫자가 달라진다."""
    old = json.loads((ROOT / "data" / "final_eval.json").read_text())["now"]
    return sum(x["correct"] for x in old), sum(x["cost"] for x in old) / len(old)


def html(dev, new):
    a, b = by_type(dev), by_type(new)
    ok, cost = then()
    rows = "".join(
        f"<tr><td>{n}</td><td class=num>{a[t][0]}/{a[t][1]}</td><td class=num>{b[t][0]}/{b[t][1]}</td></tr>"
        for t, n in TYPES
    )
    miss = "".join(
        f"<tr><td>{x['id']}</td><td>{final.qs[x['id']]['q']}</td><td>{x['near']} ({x['sim']})</td></tr>"
        for x in new
        if not x["correct"]
    )
    tot = lambda r: f"{sum(x['correct'] for x in r)}/{len(r)}"
    return page(
        "개발 세트 vs 처음 보는 문항",
        "<h1>보던 시험지 vs 처음 보는 시험지</h1>"
        "<p class=sub>같은 날 · 같은 워크벤치 · deepseek-v4-flash · 유형 비율 같음</p>"
        f"<p class=sub>참고: 같은 개발 20문항을 22편(10/17)에 돌린 기록 = 정답 {ok}/20 · 문항당 ${cost:.4f} · "
        f"오늘 = 정답 {sum(x['correct'] for x in dev)}/20 · 문항당 ${sum(x['cost'] for x in dev) / len(dev):.4f}</p>"
        f"<table><tr><th>유형</th><th>개발 20(13~22편)</th><th>처음 보는 20</th></tr>{rows}"
        f"<tr><th>합계</th><th class=num>{tot(dev)}</th><th class=num>{tot(new)}</th></tr></table>"
        f"<h2>처음 보는 문항 중 틀린 것</h2><table><tr><th>id</th><th>질문</th><th>가장 닮은 개발 문항(유사도)</th></tr>{miss}</table>",
    )


if __name__ == "__main__":
    if "--show" in sys.argv:  # 이미 돌린 결과(data/heldout24.json)로 화면만 다시 띄운다(API 호출 없음)
        d = json.loads((ROOT / "data" / "heldout24.json").read_text())
        serve(html(d["dev"], d["new"]), 8826)
        sys.exit()
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(final.run_now, DEV + NEW))
    final.mcp.close()
    dev, new = res[: len(DEV)], res[len(DEV) :]
    for x in new:
        x["near"], x["sim"] = nearest(x["id"])
    rows = [final.row("24편 · 개발 20(보던 문항)", dev), final.row("24편 · 처음 보는 20", new)]
    with (ROOT / "data" / "scorecard.jsonl").open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (ROOT / "data" / "heldout24.json").write_text(json.dumps({"dev": dev, "new": new}, ensure_ascii=False))
    for r in rows:
        print(f"{r['name']}: 정답 {r['pass_rate'] * 100:.0f}% · ${r['cost_per_q']}/문항 · p50 {r['p50_s']}초")
    ok, cost = then()
    print(f"  참고: 같은 개발 20문항 22편(10/17) 기록 = 정답 {ok}/20 · ${cost:.5f}/문항")
    a, b = by_type(dev), by_type(new)
    for t, n in TYPES:
        print(f"  {n:5s} 개발 {a[t][0]}/{a[t][1]} · 처음 보는 {b[t][0]}/{b[t][1]}")
    serve(html(dev, new), 8826)
