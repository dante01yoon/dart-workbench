"""34편 과제 1 풀이 — 관문이 막은 문항은 지시문 탓인가, 다시 돌릴 때의 흔들림인가.

회귀 세트에서 떨어진 3문항(n11 q35 q33)과 새로 거절한 q38을 지시문 v1 · v2로 각각 2번씩 다시 돌린다(에이전트 전체).
v1에서도 떨어지면 흔들림(또는 원래 불안정한 문항), v1에서는 맞고 v2에서만 떨어지면 지시문 탓.
사용: uv run python sec34/solutions/a1_blame.py   → data/blame34.json
"""

import importlib.util
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "sec34"))
from planner_v2 import PLANNER_V2

spec = importlib.util.spec_from_file_location("run26", ROOT / "sec26" / "01_run.py")
run26 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run26)
wb = sys.modules["workbench"]
V1 = wb.PLANNER
sys.path.insert(0, str(ROOT / "sec33"))
from regress import check

IDS = ["n11", "q35", "q33", "q38"]
items = [x for x in run26.ITEMS if x["id"] in IDS] * 2
res, cost = {}, 0.0
for name, prompt in (("v1", V1), ("v2", PLANNER_V2)):
    wb.PLANNER = prompt  # 한 번에 한 지시문만 — 같은 모듈 값을 바꾸므로 v1 · v2를 섞어 돌리지 않는다
    with ThreadPoolExecutor(8) as ex:
        outs = list(ex.map(run26.run, items))
    for x in outs:
        row = {
            "report": [s["sentence"] for s in x["report"]],
            "evidence": [e["claim"] for e in x.get("evidence", [])],
        }
        ok = check({**row, "keys": x["keys"], "type": x["type"], "refused": x["refused"], "id": x["id"]})
        res.setdefault(x["id"], {}).setdefault(name, []).append(ok)
        cost += x["cost"]
run26.final.mcp.close()
print("\n문항   v1(2번)  v2(2번)  판정")
for i in IDS:
    a, b = res[i]["v1"], res[i]["v2"]
    verdict = "지시문 탓" if all(a) and not any(b) else "흔들림 · 둘 다 불안정" if not all(a) else "섞임"
    print(f"{i}   {sum(a)}/2      {sum(b)}/2      {verdict}")
print(f"에이전트 {len(items) * 2}번 · ${cost:.4f}")
(ROOT / "data" / "blame34.json").write_text(json.dumps({"cost": round(cost, 5), "items": res}, indent=1))
