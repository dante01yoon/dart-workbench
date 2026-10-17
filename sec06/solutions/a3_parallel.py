"""과제 3 풀이: 서브에이전트 4개를 동시에 돌리면 얼마나 빨라질까? (메인이 순서대로 맡기는 본편과 비교)
사용: uv run python sec06/solutions/a3_parallel.py"""

import time
from concurrent.futures import ThreadPoolExecutor

from _lab import sa

from skills import llm, loop

g = sa.gold()
t0 = time.time()


def sub(corp):
    system = (
        "너는 공시 분석가다. 아래 스킬의 절차를 따르고, 보고 첫 줄에 주당배당금(원)을 숫자로 적어라.\n\n"
        + sa.SKILL
    )
    final, calls, _ = loop(system, f"{corp} {sa.YEAR}년 배당 점검", sa.WORK)
    return corp, final, calls


with ThreadPoolExecutor(4) as ex:
    reports = list(ex.map(sub, sa.CORPS))
t_sub = time.time() - t0
msg = sa.TASK + "\n\n서브에이전트 보고:\n" + "\n\n".join(f"[{c}]\n{f}" for c, f, _ in reports)
m, u = llm([{"role": "user", "content": msg}])
cost = sum(c["cost"] for _, _, calls in reports for c in calls) + float(u.get("cost") or 0)
print(
    f"동시 실행: 주당배당금 {sa.score(m.get('content') or '', g)}/4  서브 {t_sub:.0f}초 + 메인 {time.time() - t0 - t_sub:.0f}초 = {time.time() - t0:.0f}초  ${cost:.4f}"
)
