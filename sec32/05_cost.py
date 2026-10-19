"""32편 ⑤ 비용 · 지연 — 질문당 비용과 시간, 성공 1건당 비용, 비용 상한이 실제로 지켜졌나.

- 재료: 26편 실행 기록의 cost(그 문항에서 쓴 돈, 워크벤치 wb.spent) · seconds(걸린 시간) · 이벤트의 spent(그 시점까지 쓴 돈).
- 상한 검사: 워크벤치 상한은 문항당 $0.05. 기록된 최고 비용이 상한 아래인가, 그리고 상한을 낮추면
  어느 문항이 어느 단계에서 멈췄을지(이벤트의 spent가 처음 상한을 넘는 곳 — 기록된 시점 기준 근사)를 다시 계산한다.
모델 호출 없음. 사용: uv run python sec32/05_cost.py → data/eval32_cost.json
"""

from statistics import median

from agent_eval import save, traces

xs = traces()
cost, secs = [x["cost"] for x in xs], [x["seconds"] for x in xs]
ok = [x for x in xs if x["correct"]]


def p95(v):
    v = sorted(v)
    return v[min(len(v) - 1, round(0.95 * (len(v) - 1)))]


print(f"26편 실행 {len(xs)}문항 (deepseek-v4-flash, 6개 동시, 2026-10-19)")
print(
    f"  비용  합계 ${sum(cost):.4f} · 중앙값 ${median(cost):.4f} · p95 ${p95(cost):.4f} · 최고 ${max(cost):.4f}"
)
print(f"  시간  중앙값 {median(secs):.0f}초 · p95 {p95(secs):.0f}초 · 최고 {max(secs):.0f}초")
print(
    f"  성공 1건당 비용 = 합계 / 정답 {len(ok)}개 = ${sum(cost) / len(ok):.4f}  (문항당 평균 ${sum(cost) / len(xs):.4f}보다 비싸다)"
)
slow = sorted(xs, key=lambda x: -x["seconds"])[:3]
print("  가장 느린 문항 " + " · ".join(f"{x['id']} {x['seconds']:.0f}초 ${x['cost']:.4f}" for x in slow))

STEP = {
    "plan": "계획",
    "task_end": "도구 · 근거 뽑기",
    "verify": "작성 · 심판",
}  # 작성 비용은 따로 기록이 없어 다음 심판 기록에 합쳐 보인다


def cut(x, cap):
    """상한이 cap이었다면 처음 넘는 단계(없으면 None)."""
    return next((STEP[e["type"]] for e in x["events"] if e.get("spent", 0) > cap and e["type"] in STEP), None)


print("\n비용 상한 검사 (워크벤치 상한 문항당 $0.05)")
print(
    f"  상한을 넘은 문항 {sum(c > 0.05 for c in cost)}개 · 상한 중단(budget 이벤트) {sum(any(e['type'] == 'budget' for e in x['events']) for x in xs)}개"
)
rows = []
for cap in (0.05, 0.01, 0.005, 0.003):
    hit = [(x, cut(x, cap)) for x in xs if cut(x, cap)]
    lost = [x for x, _ in hit if x["correct"]]
    where = {}
    for _, s in hit:
        where[s] = where.get(s, 0) + 1
    rows.append({"cap": cap, "cut": len(hit), "lost": len(lost), "where": where})
    print(
        f"  상한 ${cap:<5} → 멈출 문항 {len(hit):2d}개(그중 정답이던 것 {len(lost):2d}개)"
        + (f"  멈추는 단계: {', '.join(f'{k} {v}' for k, v in where.items())}" if where else "")
    )
save(
    "eval32_cost.json",
    {"n": len(xs), "sum": sum(cost), "median": median(cost), "p95": p95(cost), "max": max(cost),
     "sec_median": median(secs), "sec_p95": p95(secs), "sec_max": max(secs), "correct": len(ok),
     "per_success": sum(cost) / len(ok), "caps": rows},
)  # fmt: skip
print("기록 → data/eval32_cost.json")
