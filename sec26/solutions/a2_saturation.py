"""26편 과제 2 — 포화 곡선: 메모를 읽은 순서대로 하나씩 더할 때, 지금까지 나온 유형 수(모델 호출 없음, 저장된 묶음 사용).
사용: uv run python sec26/solutions/a2_saturation.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
memos = list(json.loads((ROOT / "data" / "memos26.json").read_text()))  # 녹화에서 입력한 순서
groups = json.loads((ROOT / "data" / "groups26.json").read_text())["groups"]
kind = {i: g["name"] for g in groups for i in g["ids"]}
seen, curve = set(), []
for k, i in enumerate(memos, 1):
    seen.add(kind[i])
    curve.append(len(seen))
    print(f"{k:2d}번째 메모 {i}: 유형 {len(seen)}개 {'█' * len(seen)}  ({kind[i]})")
last_new = max(k for k in range(1, len(curve) + 1) if k == 1 or curve[k - 1] > curve[k - 2])
print(
    f"\n마지막으로 새 유형이 나온 메모: {last_new}번째 / {len(memos)}개 — 끝까지 새 유형이 나오면 아직 포화가 아니다"
)
