"""과제 2 풀이: 서브에이전트에게 "주당배당금 금액을 꼭 보고하라"고 시키면 비교표가 4/4가 될까?
사용: uv run python sec06/solutions/a2_report.py"""

from _lab import sa

sa.REPORT = "보고 첫 줄에 2025년 보통주 주당배당금(원)과 배당성향(%)을 숫자로 적고, 나머지는 짧게 보고하라."
r = sa.team(sa.gold())
sub_total = sum(sum(s["calls"]) for s in r["subs"])
print(
    f"주당배당금 {r['ok']}/4  메인 입력 {sum(r['main']):,}  서브 입력 {sub_total:,}  ${r['cost']:.4f}  {r['seconds']}초"
)
