"""32편 ③ 도구 궤적 — 최종 답 말고, 에이전트가 거쳐 간 길을 코드로 채점한다.

검사 네 가지(계획 이벤트의 작업 목록 = 도구 호출):
1. 필요한 도구: 재무 API 계정(매출 · 영업이익 · 당기순이익 · 실적)을 묻으면 회사마다 financials, 그 밖의 사실은 filings,
   투자 권유는 도구 없이 거절, 근거 없음 문항도 공시(filings)부터 확인.
2. 인자: 회사 인자가 질문의 회사인가, 검색어의 연도가 질문이 가리키는 연도인가("작년" = 2025, "전년" = 하나 앞).
3. 중복 호출: 같은 회사에 같은 도구를 두 번(재무 API는 한 번에 두 해를 준다).
4. 순서: 계획 → 도구 → 작성 → 심판 → (반성) → 끝. 단계 수(도구 호출 · 반성)는 분포로 본다.
모델 호출 없음. 사용: uv run python sec32/03_trajectory.py → data/eval32_trajectory.json
"""

import re
from collections import Counter

from agent_eval import corps_in, plan, save, traces

API = re.compile(r"매출|영업이익|당기순이익|실적")
YEAR = re.compile(r"(20\d\d)년?")


def expected(x):
    """질문 → 꼭 불러야 할 (도구, 회사) 묶음. 거절 문항은 빈 집합(도구 없이 거절)."""
    cs = corps_in(x["q"]) or ["?"]
    if x["type"] == "refuse":
        return set()
    worker = "financials" if API.search(x["q"]) and x["type"] != "none" else "filings"
    return {(worker, c) for c in cs}


def allowed_years(q):
    ys = {int(y) for y in YEAR.findall(q)} or {2025}
    if "작년" in q:
        ys = {2025}
    if re.search(r"전년|대비", q):
        ys |= {min(ys) - 1}
    return ys


def check(x):
    tasks = plan(x) or []
    have = {(t["worker"], t.get("corp")) for t in tasks}
    need = expected(x)
    refused = any(e["type"] == "refused" for e in x["events"])
    problems = []
    if x["type"] == "refuse":
        if not refused:
            problems.append("거절 안 함")
    else:
        problems += [f"{w} 없음({c})" for w, c in sorted(need - have)]
    cs = corps_in(x["q"])
    problems += [f"회사 인자 {t.get('corp')}" for t in tasks if cs and t.get("corp") not in cs]
    ys = allowed_years(x["q"])
    problems += [f"연도 인자 {y}" for t in tasks for y in {int(y) for y in YEAR.findall(t["query"])} - ys]
    dup = [k for k, n in Counter((t["worker"], t.get("corp")) for t in tasks).items() if n > 1]
    problems += [f"중복 {w}×2({c})" for w, c in dup if w != "filings"]  # 공시 검색은 검색어가 다르면 다른 일
    order = [
        e["type"] for e in x["events"] if e["type"] in ("plan", "task_start", "writing", "verify", "done")
    ]
    if order and order != sorted(order, key=["plan", "task_start", "writing", "verify", "done"].index):
        problems.append("순서")
    return {
        "id": x["id"],
        "q": x["q"],
        "correct": x["correct"],
        "tools": [f"{t['worker']}({t.get('corp')})" for t in tasks],
        "calls": len(tasks),
        "revise": sum(e["type"] == "revise" for e in x["events"]),
        "problems": list(dict.fromkeys(problems)),
    }


assert allowed_years("하이닉스 작년 영업이익 얼마야?") == {2025}
assert allowed_years("삼성전자 연구개발비 비율은 전년보다 늘었나") == {2024, 2025}

rows = [check(x) for x in traces()]
ok = [r for r in rows if not r["problems"]]
print(f"궤적 채점 {len(rows)}문항 — 네 검사 모두 통과 {len(ok)}/{len(rows)}")
for name in ("없음", "거절", "회사 인자", "연도 인자", "중복", "순서"):
    hit = [r["id"] for r in rows if any(name in p for p in r["problems"])]
    print(f"  {name:6s} {len(hit):2d}  {' '.join(hit)}")
calls = Counter(r["calls"] for r in rows)
print("  도구 호출 수 분포 " + " · ".join(f"{k}번 {calls[k]}문항" for k in sorted(calls)))
print(f"  반성(고쳐 쓰기)한 문항 {sum(r['revise'] > 0 for r in rows)}/{len(rows)}")

print("\n최종 답 × 궤적")
cell = lambda c, t: [r for r in rows if r["correct"] == c and (not r["problems"]) == t]
print(
    f"  답 맞음 · 궤적 통과 {len(cell(True, True)):2d}   답 맞음 · 궤적 문제 {len(cell(True, False)):2d}  ← 최종 답만 보면 놓친다"
)
print(f"  답 틀림 · 궤적 통과 {len(cell(False, True)):2d}   답 틀림 · 궤적 문제 {len(cell(False, False)):2d}")
for r in cell(True, False):
    print(f"    맞음인데 {r['id']:4s} {', '.join(r['problems'])}  ← {r['q'][:22]}")
for r in cell(False, False):
    print(f"    틀림 {r['id']:4s} {', '.join(r['problems'])}  ← {r['q'][:22]}")
save("eval32_trajectory.json", rows)
print("기록 → data/eval32_trajectory.json")
