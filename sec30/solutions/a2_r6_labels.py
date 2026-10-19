"""30편 과제 2 — R6 원본 8개에 사람 라벨이 없으면 판사 TNR은 "모른다". 판사가 '아니오'라고 한 3개(q17 · n10 · q49)의
라벨에 따라 TNR이 얼마나 바뀌는지 잰다. 라벨링 페이지(01_label_page.py)에서 단 라벨이 있으면 그 값도 함께 쓴다. 모델 호출 없음.
사용: uv run python sec30/solutions/a2_r6_labels.py
"""

import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from labels import DATA, TRACES
from metrics import confusion, summary, wilson

V = importlib.import_module("02_validate")
B = json.loads((DATA / "judge29.json").read_text())["b"]
judge = {(r["id"] + "+" if r["fake"] else r["id"]): r["one"] for r in B}
orig = [r["id"] for r in B if not r["fake"]]
flag = [r["id"] for r in B if not r["fake"] and r["one"] is False]
fakes = {r["id"] + "+": False for r in B if r["fake"]}
clean = {i: True for i in orig if i not in flag}  # 판사가 통과시킨 5개는 통과로 둔다(사람이 읽어 확인할 몫)
for name, lab in (("3개 모두 통과", {i: True for i in flag}), ("3개 모두 실패", {i: False for i in flag})):
    s = summary(confusion(fakes | clean | lab, judge))
    lo, hi = s["tnr_ci"]
    print(V.line(name, s) + f"  TNR 95% {lo * 100:.0f}~{hi * 100:.0f}%")
# 판사가 짚은 문장이 원문 인용에 있나(사람이 라벨링 페이지에서 보는 것과 같은 화면 정보)
SPOT = {"q17": "62,796,038주(30.67%)", "n10": "2024.07.08", "q49": "광고, 커머스 관련한 다양한 비즈니스 툴"}
for i in flag:
    hit = [e["id"] for e in TRACES[i]["evidence"] if SPOT[i] in e.get("quote", "")]
    print(
        f"  {i}: 원문 인용에 '{SPOT[i]}' → {' · '.join(hit) or '없음'} / 요약(claim)에는 "
        f"{'있음' if any(SPOT[i] in e['claim'] for e in TRACES[i]['evidence']) else '없음'}"
    )
lo, hi = wilson(5, 8)
print(f"참고: 원본 8개 중 통과 5개만 맞힌 TNR 5/8의 95% 구간 {lo * 100:.0f}~{hi * 100:.0f}%")
