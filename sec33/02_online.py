"""33편 ② 오프라인 vs 온라인 — 운영에서는 정답 키가 없다. 정답 없이 볼 수 있는 신호가 오프라인 정답과 얼마나 맞나?

우리에게는 운영 트래픽이 없다. 그래서 26편 53문항 기록을 "하루치 운영 로그"라고 치고,
운영에서도 바로 셀 수 있는 신호(빈 답 · 판사 부족 배지 · 반성 · 느림 · 비쌈)를 세어,
정답을 아는 오프라인 채점(01_gate와 같은 결과)과 맞춰 본다. 모델 호출 0.
사용: uv run python sec33/02_online.py → data/online33.json
"""

import json
from math import sqrt

from regress import ROOT, runs, score

xs = runs()
ok = score(xs)
wrong = [x for x in xs if not ok[x["id"]]]
base = len(wrong) / len(xs)
SIGNALS = {  # 운영 로그에 이미 있는 값만 쓴다(정답 키 없이)
    "빈 답": lambda x: not x["report"],
    "판사 부족 배지": lambda x: any(b != "지지" for b in x["badges"]),
    "반성(다시 쓰기)": lambda x: x["reflected"],
    "느림 300초 넘음": lambda x: x["seconds"] > 300,
    "비쌈 1센트 넘음": lambda x: x["cost"] > 0.01,
}
print(f"운영 로그라고 친 기록 {len(xs)}개 — 오프라인 채점으로는 틀린 답 {len(wrong)}개({base:.0%})")
rows = []
for name, f in SIGNALS.items():
    hit = [x for x in xs if f(x)]
    bad = sum(not ok[x["id"]] for x in hit)
    rows.append({"signal": name, "flagged": len(hit), "wrong": bad, "caught": bad, "of": len(wrong)})
    print(
        f"  {name}: 걸린 기록 {len(hit)}개 · 그중 틀림 {bad}개({bad / len(hit):.0%}) · 틀린 답 {len(wrong)}개 중 {bad}개를 잡음"
    )
print(
    f"  → 어느 신호도 정답이 아니다. 반성이 걸린 기록을 먼저 읽으면 틀린 답을 무작위({base:.0%})보다 자주 만난다."
)

print("\n하루 1,000건이 온다고 치면(가정) — 몇 %를 뽑아 사람 · 판사가 읽어야 실패율을 믿을 수 있나")
p = base
for rate in (0.01, 0.05, 0.10, 0.30):
    n = round(1000 * rate)
    print(f"  {rate:>4.0%} 표본 {n:>4}건 → 실패율 {p:.0%} ± {1.96 * sqrt(p * (1 - p) / n) * 100:.0f}%p (95%)")
(ROOT / "data" / "online33.json").write_text(
    json.dumps({"n": len(xs), "wrong": len(wrong), "signals": rows}, ensure_ascii=False, indent=1)
)
print("기록 → data/online33.json")
