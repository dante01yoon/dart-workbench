"""과제 1 풀이: 부록 예시를 4개 → 1개(삼성전자 2025)로 줄이면 전부 넣기와 점진적 노출 중 어느 쪽이 유리할까?
사용: uv run python sec06/solutions/a1_appendix.py"""

from concurrent.futures import ThreadPoolExecutor

from _lab import sk

import skills

skills.EXAMPLES = [("삼성전자", 2025)]
print("부록 합계", sum(len(skills.body(n, True)) for n in skills.SKILLS), "자")
for mode in ("all", "progressive"):
    with ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(lambda t, m=mode: sk.run(t[0], t[1], m, True), sk.TASKS))
    n = len(rows)
    print(
        f"{sk.LABEL[mode]:3s} 지시 준수 {sum(r['follows'] for r in rows)}/{n}  "
        f"과제당 입력 {sum(r['prompt_tokens'] for r in rows) // n:,}토큰  ${sum(r['cost'] for r in rows):.4f}"
    )
