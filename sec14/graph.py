"""14편 공용: 12편 리서치 팀을 LangGraph 상태 그래프로.

planner → approve(사람 승인, interrupt) → worker × N (Send로 병렬) → writer
- 상태(State)에 질문 · 작업 · 근거 · 보고서를 모은다. 근거는 워커마다 더해진다(operator.add).
- 체크포인터를 붙이면 단계마다 상태가 저장된다 → 중간에 죽어도 같은 thread_id로 이어서 돈다.
- 워커 · 프롬프트는 12편 Team의 것을 그대로 쓴다(바뀐 건 흐름을 짜는 방식뿐).
"""

import operator
import os
import sys
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec12"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec10"))
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt
from team import MAX_TASKS, PLANNER, WRITER, Team, clean_task, norm

TEAM = Team()


class State(TypedDict, total=False):
    question: str
    tasks: list
    evidence: Annotated[list, operator.add]  # 병렬 워커들이 낸 근거를 이어 붙인다
    report: list
    refused: bool


class Task(TypedDict):
    task: dict


def planner(s: State):
    plan, _ = TEAM.llm(PLANNER, f"질문: {s['question']}")
    if plan.get("refuse"):
        return {"refused": True, "tasks": []}
    tasks = [
        c
        for c in (
            clean_task(t)
            for t in plan.get("tasks", [])
            if t.get("worker") in ("filings", "news", "financials")
        )
        if c
    ]
    return {"refused": False, "tasks": [{**t, "id": f"t{n}"} for n, t in enumerate(tasks[:MAX_TASKS], 1)]}


def approve(s: State):
    """사람 승인: 계획을 보여 주고 멈춘다. 다시 실행할 때 넘긴 값(뺄 작업 번호 목록)이 여기로 돌아온다."""
    if s.get("refused") or os.environ.get("AUTO_APPROVE") == "1":
        return {}
    drop = interrupt({"tasks": s["tasks"]})
    return {"tasks": [t for t in s["tasks"] if t["id"] not in (drop or [])]}


def fan_out(s: State):
    if s.get("refused") or not s.get("tasks"):
        return "writer"
    return [Send("worker", {"task": t}) for t in s["tasks"]]  # 작업마다 worker를 하나씩 띄운다 → 병렬


def worker(x: Task):
    t = x["task"]
    if os.environ.get("CRASH") == t["worker"]:  # 실습용: 이 워커를 일부러 죽인다
        raise RuntimeError(f"{t['worker']} 워커가 죽었습니다(실습용)")
    fn = {"filings": TEAM.w_filings, "news": TEAM.w_news, "financials": TEAM.w_financials}[t["worker"]]
    ev, _ = fn(t)
    for e in ev:
        e["task"] = t["id"]
        e["verified"] = len(norm(e["quote"])) >= 10 and norm(e["quote"]) in norm(e.pop("text", ""))
    return {"evidence": ev}


def writer(s: State):
    if s.get("refused"):
        return {"report": []}
    usable = [e for e in s.get("evidence", []) if e["verified"]]
    for n, e in enumerate(usable, 1):
        e["id"] = f"e{n}"
    blob = "\n".join(f'{e["id"]} [{e["source"]}] {e["claim"]} — "{e["quote"]}"' for e in usable)
    rep, _ = TEAM.llm(WRITER, f"질문: {s['question']}\n\n[근거]\n{blob}", max_tokens=10000)
    ids = {e["id"] for e in usable}
    return {
        "report": [{**r, "cites": [c for c in r.get("cites", []) if c in ids]} for r in rep.get("report", [])]
    }


def build(checkpointer=None):
    g = StateGraph(State)
    g.add_node("planner", planner)
    g.add_node("approve", approve)
    g.add_node("worker", worker)
    g.add_node("writer", writer)
    g.add_edge(START, "planner")
    g.add_edge("planner", "approve")
    g.add_conditional_edges("approve", fan_out, ["worker", "writer"])
    g.add_edge("worker", "writer")
    g.add_edge("writer", END)
    return g.compile(checkpointer=checkpointer)
