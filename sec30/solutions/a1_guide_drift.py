"""30편 과제 1 — 지침이 바뀌면 라벨도 바뀐다(기준 표류). "근거 없음"을 공시 기준(v1)에서 공시 + 뉴스 기준(v2)으로 바꾸면
어느 문항을 다시 라벨링해야 하고, 채점기 검증 숫자는 어떻게 바뀌나? 모델 호출 없음.
v2 규칙: 뉴스 출처의 예정 · 전망을 "공시에서 확인되지 않음"과 함께 전망으로 밝히면 통과. 전망 숫자를 실적 · 사실처럼 쓰면 여전히 실패.
사용: uv run python sec30/solutions/a1_guide_drift.py
"""

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from labels import MEMOS, TRACES
from metrics import confusion, summary

V = importlib.import_module("02_validate")

scope = [i for i, x in TRACES.items() if x["type"] == "none"]  # 지침 v2가 건드리는 문항 = 근거 없음 유형
# 메모를 v2 규칙으로 다시 읽는다: q51 '사실처럼' · q52 '실적처럼' → 여전히 실패, q54 뉴스 예정 + '확인되지 않습니다' → 통과
V2 = {"q51": False, "q52": False, "q54": True}
print(f"다시 볼 문항(근거 없음 유형): {len(scope)}개 — {' · '.join(scope)}")
for i in scope:
    print(f"  {i}: {MEMOS[i]['memo'][:46]}… → v2 {'통과' if V2[i] else '실패'}")
human, judges = V.overall()
for name, h in (("지침 v1", human), ("지침 v2", human | V2)):
    print(f"{name}: 사람 실패 {sum(not v for v in h.values())}/53")
    for k in ("채점기 v2(22편)", "채점기 v3(28편)"):
        s = summary(confusion(h, judges[k]))
        print(V.line(k, s))
