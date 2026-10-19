"""34편 ② 지시문 v2로 에이전트를 다시 돌린다 — 영향받은 문항 + 회귀 세트만.

- 영향받은 문항: 26편 계획 실패 6개(고치려던 것).
- 회귀 세트 35개(33편): 계획 담당은 모든 질문에 쓰이므로, 고치다 다른 걸 망가뜨리지 않았는지 본다.
- 능력 세트의 나머지 12개는 돌리지 않는다(비용). 그 12개는 이번 변경의 효과를 말하지 않는다.
실행은 26편 01_run.py의 run()을 그대로 쓰고, 워크벤치가 읽는 PLANNER 하나만 v2로 바꿔 끼운다.
끊겨도 다시 실행하면 이미 끝난 문항은 건너뛴다(유료 호출을 두 번 하지 않게). 합계가 상한을 넘으면 새 문항을 시작하지 않는다.
사용: uv run python sec34/02_rerun.py   → data/rerun34.jsonl(전체 기록) · sec33/runs/planner_v2.jsonl(CI용, 원문 인용 없음)
"""

import importlib.util
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from planner_v2 import PLAN_FAILS, PLANNER_V2

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("run26", ROOT / "sec26" / "01_run.py")
run26 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run26)  # 26편 실행기(워크벤치 · MCP · 22편 채점기)
sys.modules["workbench"].PLANNER = PLANNER_V2  # 바꾸는 곳은 이 한 줄뿐

CAP = 0.33  # 이번 편 유료 실행 상한 $0.40 중 다시 돌리기 몫
MAIN = [json.loads(line) for line in (ROOT / "sec33" / "runs" / "main.jsonl").open()]
REG = [x["id"] for x in MAIN if x["split"] == "regression"]
TODO = PLAN_FAILS + REG
OUT = ROOT / "data" / "rerun34.jsonl"
done = {x["id"]: x for x in map(json.loads, OUT.open())} if OUT.exists() else {}
lock = threading.Lock()


def go(item):
    with lock:
        if sum(x["cost"] for x in done.values()) > CAP:
            print(f"{item['id']}  상한 ${CAP} 넘어서 건너뜀", flush=True)
            return
    try:
        x = run26.run(item)
    except Exception as e:  # noqa: BLE001 — 한 문항이 터져도 나머지는 계속 — 기록하지 않으니 다시 실행하면 다시 시도한다
        print(f"{item['id']}  실행 오류 {type(e).__name__}: {e}", flush=True)
        return
    with lock:
        done[x["id"]] = x
        with OUT.open("a") as f:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")


items = [x for x in run26.ITEMS if x["id"] in TODO and x["id"] not in done]
print(
    f"지시문 v2로 다시 돌리기: 계획 실패 {len(PLAN_FAILS)} + 회귀 세트 {len(REG)} = {len(TODO)}문항 (남은 {len(items)})"
)
with ThreadPoolExecutor(6) as ex:
    list(ex.map(go, items))
run26.final.mcp.close()

# CI가 쓸 모양으로 얼리기(33편 00_freeze와 같은 칸) — 다시 돌리지 않은 12문항은 main 출력을 그대로 두고 rerun=false
rows = []
for m in MAIN:
    x = done.get(m["id"])
    if not x:
        rows.append({**m, "rerun": False})
        continue
    rows.append(
        {
            **{k: x[k] for k in ("id", "q", "type", "keys", "refused", "cost", "seconds")},
            "report": [s["sentence"] for s in x["report"]],
            "evidence": [e["claim"] for e in x.get("evidence", [])],
            "badges": [s.get("badge") for s in x["report"]],
            "reflected": any(e["type"] == "revise" for e in x["events"]),
            "split": m["split"],
            "rerun": True,
        }
    )
(ROOT / "sec33" / "runs" / "planner_v2.jsonl").write_text(
    "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
)
spent = sum(done[i]["cost"] for i in TODO if i in done)
print(
    f"\n{sum(i in done for i in TODO)}/{len(TODO)}문항 · ${spent:.4f} → data/rerun34.jsonl, sec33/runs/planner_v2.jsonl"
)
print("다음: python3 sec33/01_gate.py --runs planner_v2")
