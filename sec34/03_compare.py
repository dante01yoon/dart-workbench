"""34편 ③ 전후 비교 — 같은 문항(짝)으로, 31편 신뢰구간과 함께. 모델 호출 0.

- 고치려던 문항(계획 실패 6): 전 → 후
- 회귀 세트 35: 떨어진 문항이 있으면 계획이 바뀌었는지(v1 계획 vs v2 계획)까지 보여 준다 — 지시문 탓인지, 다시 돌릴 때의 흔들림인지
- 다시 돌린 41문항 전체: 문항마다 (후 − 전) 차이의 평균과 95% 신뢰구간(31편 짝 비교)
사용: uv run python sec34/03_compare.py   → data/compare34.json
"""

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sec31"))
sys.path.insert(0, str(ROOT / "sec30"))
sys.path.insert(0, str(ROOT / "sec33"))
from metrics import wilson  # 30편 윌슨 구간
from planner_v2 import PLAN_FAILS
from regress import runs, score  # 33편 — 지금 answer.py + 코드 채점기 v3
from stats import Z, paired  # 31편 짝 비교

before, after = runs("main"), runs("planner_v2")
b, a = score(before), score(after)
ids = [x["id"] for x in after if x.get("rerun")]
reg = [x["id"] for x in after if x["rerun"] and x["split"] == "regression"]
fix = [i for i in PLAN_FAILS if i in ids]
rows = {x["id"]: x for x in after}
traces = {x["id"]: x for x in map(json.loads, (ROOT / "data" / "traces26.jsonl").open())}
new = {x["id"]: x for x in map(json.loads, (ROOT / "data" / "rerun34.jsonl").open())}


def plan_line(x):
    if any(e["type"] == "refused" for e in x["events"]):
        return "거절"
    p = next((e for e in x["events"] if e["type"] == "plan"), {"tasks": []})
    return " · ".join(f"{t['worker'][:3]}({t.get('corp') or '-'})" for t in p["tasks"])


def line(name, group):
    k0, k1 = sum(b[i] for i in group), sum(a[i] for i in group)
    lo, hi = wilson(k1, len(group))
    d, s = paired([a[i] for i in group], [b[i] for i in group])
    print(
        f"  {name:9s} {k0:2d}/{len(group)} → {k1:2d}/{len(group)}   후 95% {lo:.0%}~{hi:.0%}   "
        f"차이 {d * 100:+.1f}%p (95% {(d - Z * s) * 100:+.1f} ~ {(d + Z * s) * 100:+.1f})"
    )
    return {
        "n": len(group),
        "before": k0,
        "after": k1,
        "after_ci": [lo, hi],
        "diff": d,
        "diff_ci": [d - Z * s, d + Z * s],
    }


print(f"전후 비교 — 같은 {len(ids)}문항, 지시문 v1(26편 실행) → v2(34편 다시 돌림), 코드 채점기 v3")
out = {"fix": line("계획 실패", fix), "regression": line("회귀 세트", reg), "all": line("전체 41", ids)}
print("\n고치려던 문항")
for i in fix:
    print(
        f"  {i}  {'✅' if b[i] else '❌'} → {'✅' if a[i] else '❌'}   {plan_line(traces[i])}  →  {plan_line(new[i])}"
    )
lost = [i for i in reg if b[i] and not a[i]]
print(f"\n회귀 세트에서 떨어진 문항 {len(lost)}개" + ("" if lost else " — 관문 통과"))
for i in lost:
    same = plan_line(traces[i]) == plan_line(new[i])
    print(
        f"  {i}  {rows[i]['q'][:30]}   계획 {'같음' if same else '바뀜'}: {plan_line(traces[i])} → {plan_line(new[i])}"
    )
c0 = [traces[i]["cost"] for i in ids]
c1 = [new[i]["cost"] for i in ids]
s0 = [traces[i]["seconds"] for i in ids]
s1 = [new[i]["seconds"] for i in ids]
print(
    f"\n비용 · 시간(문항당 중앙값)  ${statistics.median(c0):.4f} → ${statistics.median(c1):.4f}   "
    f"{statistics.median(s0):.0f}초 → {statistics.median(s1):.0f}초   이번 다시 돌리기 합계 ${sum(c1):.4f}"
)
out.update(
    lost=lost,
    items={i: {"q": rows[i]["q"], "split": rows[i]["split"], "before": b[i], "after": a[i],
               "plan_before": plan_line(traces[i]), "plan_after": plan_line(new[i])} for i in ids},
    cost={"median_before": statistics.median(c0), "median_after": statistics.median(c1), "rerun_total": sum(c1)},
    seconds={"median_before": statistics.median(s0), "median_after": statistics.median(s1)},
)  # fmt: skip
(ROOT / "data" / "compare34.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print("기록 → data/compare34.json")
