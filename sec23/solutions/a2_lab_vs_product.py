"""과제 2 풀이: 공고를 모델 연구소(J1~J5)와 제품 회사(J6~J12)로 나눠 역량 순위가 어떻게 다른지 본다.
사용: uv run python sec23/solutions/a2_lab_vs_product.py
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "skills", Path(__file__).resolve().parents[1] / "02_job_skills.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
name = {s["id"]: s["name"] for s in m.J["skills"]}
groups = {k: [j for j in m.J["jobs"] if j["kind"] == k] for k in ("lab", "product")}
share = {k: {s: c / len(js) for s, c in m.counts(js).items()} for k, js in groups.items()}
print(
    f"연구소 {len(groups['lab'])}개 · 제품 회사 {len(groups['product'])}개 (비율 = 그 묶음에서 이 역량을 적은 공고 비율)"
)
for s in sorted(name, key=lambda s: share["product"][s] - share["lab"][s]):
    gap = share["product"][s] - share["lab"][s]
    if abs(gap) >= 0.3:
        print(
            f"{'제품 회사 쪽' if gap > 0 else '연구소 쪽'} {name[s]}: 연구소 {share['lab'][s]:.0%} · 제품 {share['product'][s]:.0%}"
        )
