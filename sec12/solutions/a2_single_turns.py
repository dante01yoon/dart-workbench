"""과제 2 풀이: 단일 에이전트의 턴 상한을 10 → 20으로 늘리면 비교 질문을 끝까지 답할까? 도구 호출 · 시간 · 비용을 본다.
사용: uv run --group frameworks python sec12/solutions/a2_single_turns.py"""

import _lab  # noqa: F401
from single import run
from team import Team

q = "삼성전자와 SK하이닉스의 2025년 실적과 위험 요인을 비교해 줘"
store = Team().store
for turns in (10, 20):
    r = run(q, store, max_turns=turns)
    tools = [c["who"] for c in r["calls"]]
    print(
        f"턴 상한 {turns}: 도구 {len(tools)}번 · {r['seconds']}초 · ${r['cost']:.4f} · 답 {len(r['answer'])}자"
    )
    print(f"   도구 순서: {' → '.join(tools)}")
    print(f"   답 앞부분: {r['answer'][:90]!r}")
