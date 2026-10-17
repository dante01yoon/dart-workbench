"""12편 ① 리서치 팀 한 번 돌려 보기: 계획 → 워커 병렬 → 보고서. 시간 막대와 인용 검사(원문에 그대로 있는 인용 수)를 본다.
사용: uv run --group frameworks python sec12/01_team.py ["질문"]"""

import sys

from team import Team

q = " ".join(sys.argv[1:]) or "현대자동차의 2025년 실적과 최근 관세 관련 뉴스를 같이 정리해 줘"
r = Team().run(q, parallel=True)
print(f"질문: {q}\n")
for x in r["timeline"]:
    bar = " " * int(x["start"]) + "█" * max(1, int(x["end"] - x["start"]))
    label = f"{x['who']:10s} {(x.get('corp') or ''):6s} {x.get('query', '')[:22]:22s}"
    print(f"  {label} {x['start']:5.1f}→{x['end']:5.1f}s  근거 {x['n']}  {bar[:60]}")
print(
    f"\n인용이 원문에 그대로 있음 {r['quote_ok']} · 빈 답 다시 부름 {r['retries']}번 · {r['seconds']}초 · ${r['cost']:.4f}\n"
)
for s in r["report"]:
    print(f"  {'●' if s['cites'] else '○'} {s['sentence']} {s['cites']}")
