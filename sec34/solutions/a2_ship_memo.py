"""34편 과제 2 풀이 — "출시해도 되나요?"에 답하는 판정 메모를 숫자로(23편 과제 3을 개선 뒤 숫자로 다시). 모델 호출 0.

규칙: 막는 조건(관문 · 위험한 실패)을 먼저 보고, 통과한 것 · 아직 모르는 것을 나눠 적는다.
사용: uv run python sec34/solutions/a2_ship_memo.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
C = json.loads((ROOT / "data" / "compare34.json").read_text())
fix, reg = C["fix"], C["regression"]
rt = (
    json.loads((ROOT / "data" / "redteam32_fact.json").read_text())
    if (ROOT / "data" / "redteam32_fact.json").exists()
    else None
)

block = []
if C["lost"]:
    block.append(
        f"회귀 세트에서 {len(C['lost'])}문항이 떨어졌다({' '.join(C['lost'])}) — 원인을 읽기 전에는 내보내지 않는다"
    )
passed = [
    f"계획 실패 {fix['before']}/{fix['n']} → {fix['after']}/{fix['n']} (후 95% {fix['after_ci'][0]:.0%}~{fix['after_ci'][1]:.0%})",
    "투자 권유 · 인젝션 · 범위 밖 레드팀 9/9 (32편)",
]
unknown = [
    "사실처럼 쓴 가짜 문장(문서 속 주입)은 4번 중 3번 뚫렸다(32편 과제 3) — 방어 한 줄 뒤 2/2지만 표본이 작다",
    "능력 세트 나머지 12문항은 이번에 다시 돌리지 않았다",
    "판사 검증은 dev 라벨 14개 · 라벨러 1명(30편)",
]
if not C["lost"]:
    passed.insert(1, f"회귀 세트 {reg['after']}/{reg['n']} — 관문 통과")
verdict = "보류" if block else "조건부 출시(내부 사용자 · 근거 카드 함께 · 가짜 사실 방어 추가 뒤 넓힘)"
print(f"판정: {verdict}\n")
for title, xs in (("막는 조건", block or ["없음"]), ("통과", passed), ("아직 모름 · 위험", unknown)):
    print(title)
    for x in xs:
        print("  -", x)
