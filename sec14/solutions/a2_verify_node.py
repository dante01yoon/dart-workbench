"""과제 2 풀이: writer 뒤에 13편 심판을 verify 노드로 붙이고, '부족' 문장이 있으면 보고서에서 빼거나 표시한다.
사용: uv run --group frameworks python sec14/solutions/a2_verify_node.py"""

import os
import sys
from pathlib import Path

os.environ["AUTO_APPROVE"] = "1"
import _lab  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sec13"))
import graph
from langgraph.graph import END, START, StateGraph
from verify import badge_sentences


def verify_node(s):
    usable = [e for e in s.get("evidence", []) if e["verified"]]
    rows = badge_sentences(s["report"], usable)
    return {
        "report": [
            {**r, "sentence": r["sentence"] if r["badge"] == "지지" else f"[{r['badge']}] {r['sentence']}"}
            for r in rows
        ]
    }


g = StateGraph(graph.State)
for name, fn in (
    ("planner", graph.planner),
    ("approve", graph.approve),
    ("worker", graph.worker),
    ("writer", graph.writer),
    ("verify", verify_node),
):
    g.add_node(name, fn)
g.add_edge(START, "planner")
g.add_edge("planner", "approve")
g.add_conditional_edges("approve", graph.fan_out, ["worker", "writer"])
g.add_edge("worker", "writer")
g.add_edge("writer", "verify")
g.add_edge("verify", END)
out = g.compile().invoke({"question": "삼성전자와 SK하이닉스의 2025년 실적과 위험 요인을 비교해 줘"})
for s in out["report"]:
    print(f"  {s['sentence']}  {s['cites']}")
    if s["badge"] != "지지":
        print(f"      ↳ {s['reason']}")
