"""과제 2 — 성공 1건당 비용을 문항 유형별로, 그리고 반성(고쳐 쓰기)을 한 문항과 안 한 문항으로 나눠 본다.

평균 하나로는 "어디에 돈이 드나"가 안 보인다. 모델 호출 없음(26편 기록).
사용: uv run python sec32/solutions/a2_cost_by_type.py
"""

import sys
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent_eval import traces

xs = traces()
print("유형           문항  정답  비용 합계   성공 1건당  시간 중앙값")
for t in sorted({x["type"] for x in xs}, key=lambda t: -sum(x["cost"] for x in xs if x["type"] == t)):
    g = [x for x in xs if x["type"] == t]
    ok = sum(x["correct"] for x in g)
    per = f"${sum(x['cost'] for x in g) / ok:.4f}" if ok else "  (정답 0)"
    print(
        f"{t:13s} {len(g):4d} {ok:5d}   ${sum(x['cost'] for x in g):.4f}   {per:>10s}  {median(x['seconds'] for x in g):6.0f}초"
    )
print()
for name, g in (
    ("반성 함", [x for x in xs if any(e["type"] == "revise" for e in x["events"])]),
    ("반성 안 함", [x for x in xs if not any(e["type"] == "revise" for e in x["events"])]),
):
    ok = sum(x["correct"] for x in g)
    print(
        f"{name:6s} {len(g)}문항 · 정답 {ok} · 문항당 ${sum(x['cost'] for x in g) / len(g):.4f} · "
        f"성공 1건당 ${sum(x['cost'] for x in g) / ok:.4f} · 시간 중앙값 {median(x['seconds'] for x in g):.0f}초"
    )
