"""과제 1 풀이: 워커 노드에 RetryPolicy를 붙이면, 한 번 죽은 워커를 그래프가 알아서 다시 부른다(체크포인트 없이도).
첫 호출만 죽는 뉴스 워커로 시험한다.
사용: uv run --group frameworks python sec14/solutions/a1_retry_policy.py"""

import os

os.environ["AUTO_APPROVE"] = "1"
import _lab  # noqa: F401
import graph
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

calls = {"news": 0}
orig = graph.TEAM.w_news


def flaky_news(t):
    calls["news"] += 1
    if calls["news"] == 1:
        raise RuntimeError("뉴스 서버 일시 오류(실습용)")
    return orig(t)


graph.TEAM.w_news = flaky_news
g = StateGraph(graph.State)
g.add_node("planner", graph.planner)
g.add_node("approve", graph.approve)
g.add_node(
    "worker",
    graph.worker,
    retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0, retry_on=RuntimeError),
)
g.add_node("writer", graph.writer)
g.add_edge(START, "planner")
g.add_edge("planner", "approve")
g.add_conditional_edges("approve", graph.fan_out, ["worker", "writer"])
g.add_edge("worker", "writer")
g.add_edge("writer", END)
out = g.compile().invoke({"question": "현대자동차의 2025년 실적과 최근 관세 관련 뉴스를 같이 정리해 줘"})
print(
    f"뉴스 워커 호출 {calls['news']}번 (첫 번은 실패) → 근거 {len(out['evidence'])}개 · 보고서 {len(out['report'])}문장"
)
