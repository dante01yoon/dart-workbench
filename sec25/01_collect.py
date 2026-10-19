"""25편 ① 실행 기록에서 질문 모으기 — 지금까지 에이전트에 실제로 던진 질문을 기록 파일에서 꺼내고,
이미 시험지(60문항 은행)에 있는 질문과 같은지 확인한다. API를 부르지 않는다.

같은 질문인지는 글자가 아니라 "회사 · 연도 · 항목"으로 본다. 글자 비슷함(3글자 묶음)으로는
"SK하이닉스 2025년 영업이익"과 q03 "SK하이닉스의 2025년 연결 영업이익은 얼마인가?"를 같은 질문으로 못 잡는다.
사용: uv run python sec25/01_collect.py → data/sec25_candidates.json
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SOURCES = [  # (기록 파일, 질문 칸, 어느 실행인가)
    ("cc_tool_count.json", "q", "16편 Claude Code 도구 실험"),
    ("team_compare.json", "q", "12편 리서치 팀"),
    ("reflect_compare.json", "q", "20편 반성 비교"),
    ("skills_runs.json", "task", "6편 스킬 실행"),
]
CORPS = {"삼성전자": "삼성전자", "삼성 전자": "삼성전자", "SK하이닉스": "SK하이닉스", "하이닉스": "SK하이닉스",
         "현대자동차": "현대자동차", "현대차": "현대자동차", "카카오": "카카오", "LG전자": "LG전자"}  # fmt: skip
ITEMS = ["영업이익률", "영업이익", "영업손실", "매출", "당기순이익", "순이익", "배당성향", "배당", "최대주주", "소액주주", "직원",
         "임원", "대표이사", "주소", "본사", "감사", "자사주", "ROE", "재고자산", "자산총계", "공시", "연구개발",
         "환율", "외환", "이자율", "원재료", "종속기업", "주가", "투자", "부문", "위험", "관세", "실적"]  # fmt: skip
SAME = {"영업손실": "영업이익", "순이익": "당기순이익", "본사": "주소"}


def slots(q):
    """질문 → (회사들, 연도, 항목들). 항목은 겹치지 않게 긴 낱말부터 뗀다(영업이익률 → 영업이익으로 또 세지 않게)."""
    corps = frozenset(v for k, v in CORPS.items() if k in q and not (k == "하이닉스" and "SK하이닉스" in q))
    years = tuple(sorted(set(re.findall(r"20\d\d", q))))
    items, rest = set(), q
    for i in ITEMS:
        if i in rest:
            items.add(SAME.get(i, i))
            rest = rest.replace(i, " ")
    return corps, years, frozenset(items)


def same(a, b):
    (ca, ya, ia), (cb, yb, ib) = slots(a), slots(b)
    return ca == cb and ia == ib and bool(ia) and (ya == yb or not ya or not yb)


def collect():
    bank = [json.loads(line) for line in (ROOT / "eval" / "questions.jsonl").open()]
    raw, seen = [], set()
    for name, key, where in SOURCES:
        for x in json.loads((DATA / name).read_text()):
            raw.append(x[key])
            if x[key] not in seen:
                seen.add(x[key])
                dup = next((b["id"] for b in bank if same(x[key], b["q"])), None)
                yield {"q": x[key], "source": where, "file": name, "dup_of": dup}
    print(f"기록 속 질문 {len(raw)}개 → 중복 빼면 {len(seen)}개")


if __name__ == "__main__":
    rows = list(collect())
    for r in rows:
        print(f"{'= ' + r['dup_of'] if r['dup_of'] else '새 질문':<8} {r['q']}  ({r['source']})")
    new = [r for r in rows if not r["dup_of"]]
    print(f"은행에 이미 있음 {len(rows) - len(new)}개 · 새 질문 {len(new)}개")
    (DATA / "sec25_candidates.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
