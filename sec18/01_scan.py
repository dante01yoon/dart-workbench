"""18편 01: 같은 서버가 업데이트로 바뀌면 guard가 무엇을 막는지 — 모델 없이 도구 목록만 받아 검사한다.
uv run python sec18/01_scan.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard import PINS, POLICY, check, fingerprint
from probe import list_tools

v1 = list_tools("v1")
pins = {"dart": {t["name"]: fingerprint(t) for t in v1 if t["name"] in POLICY["dart"]["allow_tools"]}}
PINS.parent.mkdir(exist_ok=True)
PINS.write_text(json.dumps(pins, ensure_ascii=False, indent=1))  # guard.py가 이 파일로 검사한다
print(f"■ 처음 연결(v1): 사람이 도구 정의를 확인하고 해시를 고정 → {PINS.relative_to(PINS.parent.parent)}")
for name, h in pins["dart"].items():
    print(f"   {name:<15} sha256 {h[:12]}…")

for scenario, what in [
    ("v1", "그대로"),
    ("v2_desc", "업데이트: 설명에 문장 추가"),
    ("v2_tool", "업데이트: 지우는 도구 추가"),
]:
    tools = list_tools(scenario)
    print(f"\n■ {scenario} ({what}) — 도구 {len(tools)}개")
    for t, ok, why in check("dart", tools, pins):
        print(f"   {'○' if ok else '×'} {t['name']:<15} {why}")
        if "바뀜" in why:
            old = next(x for x in v1 if x["name"] == t["name"])["description"]
            print(f"      추가된 글: 「{t['description'][len(old) :].strip()}」")

print("\n■ 허용 목록에 없는 서버(other)는 도구가 전부 막힌다:")
print("  ", [f"{t['name']} × {why}" for t, ok, why in check("other", v1, pins)][:2], "…")
