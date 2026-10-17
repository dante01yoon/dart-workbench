"""12편 리서치 팀을 LangGraph로 (강의 14편).

plan ─Send×N→ worker(병렬) → verify → approve(사람 승인, interrupt) → write
- 워커·프롬프트는 12편 Team의 것을 그대로 쓴다(비교 대상은 '조율 코드'뿐).
- 체크포인트(InMemorySaver): 승인 단계에서 멈췄다가 같은 thread_id로 이어서 실행한다.
사용: .venv/bin/python frameworks/lg_team.py "질문" [--auto-approve]
"""

import json
import operator
import sys
import time
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402
from langgraph.types import Command, Send, interrupt  # noqa: E402

from dart_rag.team import MAX_TASKS, PLANNER, WRITER, Team, clean_task, norm  # noqa: E402

team = Team()


class State(TypedDict, total=False):
    question: str
    tasks: list
    evidence: Annotated[list, operator.add]  # 병렬 워커 결과를 합친다
    log: Annotated[list, operator.add]
    approved: bool
    report: list
    t0: float


class WorkerInput(TypedDict):
    task: dict
    t0: float


def plan(state: State):
    j, tok = team._llm(PLANNER, state["question"], fast=False, max_tokens=3000)
    tasks = [clean_task(t) for t in j.get("tasks", []) if t.get("worker") in ("filings", "news", "financials")][:MAX_TASKS]
    for n, t in enumerate(tasks):
        t["id"] = f"t{n + 1}"
    return {"tasks": tasks, "t0": time.time(), "log": [{"node": "plan", "tokens": tok}]}


def fan_out(state: State):
    return [Send("worker", {"task": t, "t0": state["t0"]}) for t in state["tasks"]] or [Send("verify", state)]


def worker(inp: WorkerInput):
    t = inp["task"]
    fn = {"filings": team.w_filings, "news": team.w_news, "financials": team.w_financials}[t["worker"]]
    start = time.time() - inp["t0"]
    ev, tok = fn(t)
    return {"evidence": ev, "log": [{"node": f"worker:{t['id']}", "worker": t["worker"], "start": round(start, 1),
                                     "end": round(time.time() - inp["t0"], 1), "tokens": tok, "n": len(ev)}]}


def verify(state: State):
    """인용 문자열 검증(결정적). 결과는 기록만 하고, 실제 걸러내기는 write에서 한다(상태에 같은 목록을 두 번 더하지 않으려고)."""
    ev = state.get("evidence", [])
    ok = sum(len(norm(e["quote"])) >= 10 and norm(e["quote"]) in norm(e["text"]) for e in ev)
    return {"log": [{"node": "verify", "ok": ok, "of": len(ev)}]}


def approve(state: State):
    # 뉴스 근거가 섞이면 사람에게 확인을 받는다(공시 밖 출처). 승인 전까지 그래프가 멈춘다.
    has_news = any(e.get("kind") == "news" for e in state.get("evidence", []))
    if not has_news:
        return {"approved": True}
    ans = interrupt({"message": "뉴스 근거가 포함됐습니다. 보고서에 써도 될까요?",
                     "news": [e["source"] for e in state["evidence"] if e.get("kind") == "news"][:5]})
    return {"approved": bool(ans)}


def write(state: State):
    usable = []
    for n, e in enumerate(state.get("evidence", [])):
        ok = len(norm(e["quote"])) >= 10 and norm(e["quote"]) in norm(e["text"])
        if ok and (state.get("approved") or e.get("kind") != "news"):
            usable.append({**e, "id": f"e{n + 1}"})
    blob = "\n".join(f"{e['id']} [{e['source']}] {e['claim']} — \"{e['quote']}\"" for e in usable)
    rep, tok = team._llm(WRITER, f"질문: {state['question']}\n\n[근거]\n{blob}", fast=False, max_tokens=4000)
    ids = {e["id"] for e in usable}
    report = [{**r, "cites": [c for c in r.get("cites", []) if c in ids]} for r in rep.get("report", [])]
    return {"report": report, "log": [{"node": "write", "tokens": tok, "usable": len(usable), "all": len(state.get("evidence", []))}]}


g = StateGraph(State)
g.add_node("plan", plan)
g.add_node("worker", worker)
g.add_node("verify", verify)
g.add_node("approve", approve)
g.add_node("write", write)
g.add_edge(START, "plan")
g.add_conditional_edges("plan", fan_out, ["worker", "verify"])
g.add_edge("worker", "verify")
g.add_edge("verify", "approve")
g.add_edge("approve", "write")
g.add_edge("write", END)
graph = g.compile(checkpointer=InMemorySaver())


def run(question, auto_approve=True, thread="t1"):
    cfg = {"configurable": {"thread_id": thread}}
    t0 = time.time()
    out = graph.invoke({"question": question}, cfg)
    if "__interrupt__" in out:
        print("⏸  승인 대기:", out["__interrupt__"][0].value["message"], flush=True)
        out = graph.invoke(Command(resume=auto_approve), cfg)  # 같은 thread_id → 체크포인트에서 이어서
    tokens = sum(x.get("tokens", 0) for x in out["log"])
    return {"seconds": round(time.time() - t0, 1), "tokens": tokens, "report": out["report"], "log": out["log"],
            "green": sum(bool(r["cites"]) for r in out["report"])}


if __name__ == "__main__":
    q = " ".join(a for a in sys.argv[1:] if not a.startswith("--")) or "현대자동차의 2025년 실적과 최근 관세 관련 뉴스를 같이 정리해 줘"
    r = run(q, auto_approve=True)  # 녹화에서는 승인 화면을 보여 준 뒤 True로 이어 간다
    for x in r["log"]:
        print("  ", x)
    print(f"시간 {r['seconds']}s  토큰 {r['tokens']}  출처 있는 문장 {r['green']}/{len(r['report'])}")
    for s in r["report"]:
        print(("🟢" if s["cites"] else "🔴"), s["sentence"][:120], s["cites"])
    print(graph.get_graph().draw_mermaid())
