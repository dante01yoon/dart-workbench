"""과제 1 풀이: 바뀐 도구를 사람이 확인하고 다시 고정(재승인)한다. 무엇이 바뀌었는지 보여 주고, y일 때만 해시를 바꾼다.
uv run python sec18/solutions/a1_repin.py v2_desc        # 물어본다
uv run python sec18/solutions/a1_repin.py v2_desc --yes  # 시험용: 바로 승인
"""

import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from guard import PINS, POLICY, check, fingerprint
from probe import list_tools

SCENARIO = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "v2_desc"
pins = json.loads(PINS.read_text())
tools = list_tools(SCENARIO)
for t, ok, why in check("dart", tools, pins):
    if "바뀜" not in why:
        continue
    print(f"■ {t['name']}: {why}")
    old = next(x for x in list_tools("v1") if x["name"] == t["name"])
    for line in difflib.unified_diff([old["description"]], [t["description"]], lineterm="", n=0):
        if line[:1] in "+-" and not line.startswith(("+++", "---")):
            print("  ", line)
    yes = "--yes" in sys.argv or input("이 변경을 승인하고 다시 고정할까요? [y/N] ").strip().lower() == "y"
    if yes:
        pins["dart"][t["name"]] = fingerprint(t)
        print("   → 새 해시로 고정")
    else:
        print("   → 그대로 막아 둔다")
PINS.write_text(json.dumps(pins, ensure_ascii=False, indent=1))
print(
    "검사:",
    [
        (t["name"], why)
        for t, ok, why in check("dart", tools, pins)
        if t["name"] in POLICY["dart"]["allow_tools"]
    ],
)
