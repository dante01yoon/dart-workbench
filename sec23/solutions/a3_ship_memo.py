"""과제 3 풀이: 면접 질문 "이 에이전트를 출시해도 되나요?"에 지도 숫자로 답하는 판정 메모.
측정면마다 기준을 먼저 정하고(숫자를 보기 전에), 통과 · 미달 · 판정 불가(아직 안 잼)를 나눈다.
사용: uv run python sec23/solutions/a3_ship_memo.py
"""

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QS = {json.loads(line)["id"]: json.loads(line) for line in (ROOT / "eval" / "questions.jsonl").open()}
now = json.loads((ROOT / "data" / "final_eval.json").read_text())["now"]
ref = [x for x in now if QS[x["id"]]["type"] in ("none", "refuse")]
sent = sum(x["sentences"] for x in now)
p95 = statistics.quantiles([x["seconds"] for x in now], n=20)[-1]
CHECKS = [  # (측정면, 기준, 실제 값, 통과 여부 · None이면 판정 불가)
    ("① 정답성", "정답 90% 이상", sum(x["correct"] for x in now) / len(now), lambda v: v >= 0.9),
    ("② 인용", "출처 단 문장 95% 이상", sum(x["cited"] for x in now) / sent, lambda v: v >= 0.95),
    ("③ 거절", "거절해야 할 질문 전부 거절", sum(x["correct"] for x in ref) / len(ref), lambda v: v == 1.0),
    ("⑥ 지연", "p95 300초 이하", p95, lambda v: v <= 300),
    ("⑥ 비용", "문항당 1센트 이하", sum(x["cost"] for x in now) / len(now), lambda v: v <= 0.01),
    ("⑦ 판사", "판사를 사람 라벨로 검증", None, None),
]
for face, rule, v, ok in CHECKS:
    mark = "판정 불가(아직 안 잼)" if ok is None else ("통과" if ok(v) else "미달")
    val = "-" if v is None else (f"{v:.0%}" if v <= 1 else f"{v:.0f}초")
    print(f"{face} · {rule} · {val if face != '⑥ 비용' else f'${v:.4f}'} → {mark}")
fails = [c[0] for c in CHECKS if c[3] is not None and not c[3](c[2])]
print(
    f"결론: 미달 {len(fails)}개({', '.join(fails) or '없음'}) · 판정 불가 1개 → 아직 출시 판정을 내릴 수 없다. 20문항이라 신뢰구간도 넓다(31편)."
)
