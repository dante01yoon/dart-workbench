"""과제 1 풀이: 노력 규칙의 상한(MAX_TASKS)을 2 · 4 · 8로 바꾸면 비교 질문의 시간 · 비용 · 근거가 어떻게 달라질까?
사용: uv run --group frameworks python sec12/solutions/a1_effort.py"""

import _lab  # noqa: F401
import team as T

q = "삼성전자와 SK하이닉스의 2025년 실적과 위험 요인을 비교해 줘"
tm = T.Team()
for cap in (2, 4, 8):
    T.MAX_TASKS = cap
    r = tm.run(q)
    cited = sum(bool(s["cites"]) for s in r["report"])
    print(
        f"상한 {cap}  작업 {len(r['tasks'])}개  {r['seconds']:6.1f}초  ${r['cost']:.4f}  근거 {r['quote_ok']}  출처 단 문장 {cited}/{len(r['report'])}"
    )
    for s in r["report"]:
        if not s["cites"] or "확인되지 않" in s["sentence"]:
            print(f"      ○ {s['sentence'][:70]}")
