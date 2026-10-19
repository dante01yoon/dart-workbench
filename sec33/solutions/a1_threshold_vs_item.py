"""33편 과제 1 — 전체 점수 임계값 관문 vs 문항 단위 회귀 관문. 답 만들기를 여러 가지로 바꿔 보고 어느 관문이 막는지 센다. 모델 호출 0."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from regress import baseline, runs, score

xs = runs()
base = baseline()
reg = [x["id"] for x in xs if x["split"] == "regression"]
VARIANTS = {
    "앞 두 문장만(PR 1차)": lambda r, e: " ".join(r[:2]),
    "앞 세 문장만": lambda r, e: " ".join(r[:3]),
    "근거 요약 빼기": lambda r, e: " ".join(r),
    "앞 두 문장 + 근거 요약": lambda r, e: " ".join(r[:2]) + " " + " ".join(e),
    "근거 요약만": lambda r, e: " ".join(e),
}
b = sum(base.values()) / len(xs)
print(f"main 전체 {b:.1%} · 회귀 세트 {len(reg)}문항")
for name, make in VARIANTS.items():
    now = score(xs, make)
    d = (sum(now.values()) / len(xs) - b) * 100
    lost = [i for i in reg if not now[i]]
    gates = " · ".join(f"-{t}%p 관문 {'막음' if d <= -t else '통과'}" for t in (5, 10, 17))
    print(
        f"  {name}: 전체 {d:+.1f}%p · 회귀 {len(lost)}문항 떨어짐 → 문항 관문 {'막음' if lost else '통과'} | {gates}"
    )
