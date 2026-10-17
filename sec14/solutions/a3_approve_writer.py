"""과제 3 풀이: 사람 승인을 writer 앞에도 둔다 — 근거 목록을 보고 뺄 근거를 고른다(interrupt를 두 번).
사용: uv run --group frameworks python sec14/solutions/a3_approve_writer.py (입력 없이 돌리면 원문 일치 안 된 근거를 자동으로 뺀다)"""

import os

os.environ["AUTO_APPROVE"] = "1"
import _lab  # noqa: F401
import graph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


def review(s):
    drop = interrupt(
        {"evidence": [(i, e["claim"][:60], e["verified"]) for i, e in enumerate(s.get("evidence", []))]}
    )
    return {"dropped": drop}


def writer2(s):
    keep = [e for i, e in enumerate(s.get("evidence", [])) if i not in set(s.get("dropped") or [])]
    return graph.writer({**s, "evidence": keep})


class S2(graph.State, total=False):
    dropped: list


g = StateGraph(S2)
for name, fn in (
    ("planner", graph.planner),
    ("approve", graph.approve),
    ("worker", graph.worker),
    ("review", review),
    ("writer", writer2),
):
    g.add_node(name, fn)
g.add_edge(START, "planner")
g.add_edge("planner", "approve")
g.add_conditional_edges("approve", graph.fan_out, ["worker", "writer"])
g.add_edge("worker", "review")
g.add_edge("review", "writer")
g.add_edge("writer", END)
app = g.compile(InMemorySaver())
cfg = {"configurable": {"thread_id": "review-1"}}
out = app.invoke({"question": "카카오의 2025년 영업이익과 주요 사업 부문을 알려줘"}, cfg)
items = out["__interrupt__"][0].value["evidence"]
for i, claim, ok in items:
    print(f"  {i:2d} {'○' if ok else '×'} {claim}")
drop = [i for i, _, ok in items if not ok]
print(f"원문 일치 안 된 근거 {drop or '없음'} 빼고 작성")
out = app.invoke(Command(resume=drop), cfg)
for s in out["report"]:
    print(f"  {'●' if s['cites'] else '○'} {s['sentence']}")
