"""13편 ② 리서치 팀 평가 20문항 + 루브릭: 정답 · 출처 단 문장 · 인용 원문 일치 · 심판 지지 · 거절 · 비용 · 시간.
문항: 숫자 4 · 전년 대비 3 · 회사 비교 3 · 서술 4 · 사실 2 · 근거 없음 2 · 투자 권유 2
사용: uv run --group frameworks python sec13/02_eval.py → data/team_eval.json"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec12"))  # 12편 팀 → sec10 → sec07
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec10"))
import json
from concurrent.futures import ThreadPoolExecutor

from cite import keys, questions
from team import Team
from verify import badge_sentences
from web import ROOT

IDS = [
    "q01",
    "q03",
    "q06",
    "q09",
    "q28",
    "q30",
    "q31",
    "q36",
    "q37",
    "q40",
    "q44",
    "q45",
    "q47",
    "q49",
    "q15",
    "q17",
    "q51",
    "q54",
    "q56",
    "q59",
]
team, qs, ks = Team(), questions(), keys()


def flat(s):
    return "".join(s.split())


def grade(qid, r):
    if ks[qid] == "refuse":  # 근거 없음 · 투자 권유: 거절했거나 "확인되지 않음"만 썼으면 정답
        text = " ".join(s["sentence"] for s in r["report"])
        return r["refused"] or not r["report"] or "확인되지 않" in text
    text = flat(" ".join(s["sentence"] for s in r["report"]) + " ".join(e["claim"] for e in r["evidence"]))
    return all(any(flat(k) in text for k in g) for g in ks[qid])


def run(qid):
    r = team.run(qs[qid]["q"])
    rows = badge_sentences(r["report"], r["evidence"], workers=4)
    return {
        "id": qid,
        "type": qs[qid]["type"],
        "q": qs[qid]["q"],
        "correct": grade(qid, r),
        "refused": r["refused"],
        "report": rows,
        "evidence": r["evidence"],
        "quote_ok": r.get("quote_ok", "0/0"),
        "seconds": r["seconds"],
        "cost": r["cost"] + sum(s["cost"] for s in rows),
        "retries": r.get("retries", 0),
    }


with ThreadPoolExecutor(4) as ex:
    res = list(ex.map(run, IDS))
sents = [s for x in res for s in x["report"]]
q_ok = [tuple(map(int, x["quote_ok"].split("/"))) for x in res]
print(f"정답 {sum(x['correct'] for x in res)}/{len(res)}")
for t, name in (
    ("number", "숫자"),
    ("year_compare", "전년 대비"),
    ("cross_company", "회사 비교"),
    ("narrative", "서술"),
    ("fact", "사실"),
    ("none", "근거 없음"),
    ("refuse", "투자 권유"),
):
    rs = [x for x in res if x["type"] == t]
    print(f"  {name:5s} {sum(x['correct'] for x in rs)}/{len(rs)}")
print(
    f"출처 단 문장 {sum(s['badge'] != '출처 없음' for s in sents)}/{len(sents)} · "
    f"심판 지지 {sum(s['badge'] == '지지' for s in sents)}/{len(sents)} · "
    f"인용 원문 일치 {sum(a for a, _ in q_ok)}/{sum(b for _, b in q_ok)}"
)
print(
    f"비용 ${sum(x['cost'] for x in res):.4f} · 문항당 평균 {sum(x['seconds'] for x in res) / len(res):.0f}초 · 빈 답 다시 부름 {sum(x['retries'] for x in res)}번"
)
(ROOT / "data" / "team_eval.json").write_text(json.dumps(res, ensure_ascii=False))
print("저장 → data/team_eval.json   배지 보고서 화면: uv run python sec13/04_report_web.py")
