"""14편 ④ 직접 만든 팀(12편) vs LangGraph 그래프 — 같은 질문 3개를 병렬로 돌려 시간 · 근거 · 보고서를 재고,
흐름을 짜는 코드 줄 수와 기능(이어서 돌기 · 사람 승인 · 그래프 그림)을 비교한다.
사용: uv run --group frameworks python sec14/04_compare.py → data/lg_compare.json"""

import ast
import inspect
import json
import os
import sys
import time
from pathlib import Path

os.environ["AUTO_APPROVE"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph
from graph import TEAM, build
from team import Team
from web import ROOT

QS = [
    "카카오의 2025년 영업이익과 주요 사업 부문을 알려줘",
    "삼성전자와 SK하이닉스의 2025년 실적과 위험 요인을 비교해 줘",
    "현대자동차의 2025년 실적과 최근 관세 관련 뉴스를 같이 정리해 줘",
]


def code_lines(src):
    """빈 줄 · 주석 · 문서 문자열을 뺀 코드 줄 수."""
    src = inspect.cleandoc(src) if src.startswith(" ") else src
    tree = ast.parse(src)
    doc = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (
            isinstance(body, list)
            and body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
        ):
            doc |= set(range(body[0].lineno, body[0].end_lineno + 1))
    return sum(
        1
        for n, ln in enumerate(src.splitlines(), 1)
        if ln.strip() and not ln.strip().startswith("#") and n not in doc
    )


direct_src = inspect.getsource(Team.run) + inspect.getsource(Team.run_task)
graph_src = "\n".join(
    inspect.getsource(f)
    for f in (
        graph.State,
        graph.Task,
        graph.planner,
        graph.approve,
        graph.fan_out,
        graph.worker,
        graph.writer,
        graph.build,
    )
)
lines = {"직접": code_lines(inspect.cleandoc(direct_src)), "LangGraph": code_lines(graph_src)}
print(f"흐름 코드 줄 수  직접 {lines['직접']} · LangGraph {lines['LangGraph']}")

app, rows = build(), []
for q in QS:
    t0 = time.time()
    d = TEAM.run(q, parallel=True)
    rows.append(
        {
            "q": q,
            "impl": "직접",
            "seconds": round(time.time() - t0, 1),
            "evidence": len(d["evidence"]),
            "sentences": len(d["report"]),
            "cited": sum(bool(s["cites"]) for s in d["report"]),
        }
    )
    t0 = time.time()
    g = app.invoke({"question": q})
    rows.append(
        {
            "q": q,
            "impl": "LangGraph",
            "seconds": round(time.time() - t0, 1),
            "evidence": len(g["evidence"]),
            "sentences": len(g["report"]),
            "cited": sum(bool(s["cites"]) for s in g["report"]),
        }
    )
    print(f"■ {q}")
    for x in rows[-2:]:
        print(
            f"  {x['impl']:9s} {x['seconds']:6.1f}초  근거 {x['evidence']:2d}  출처 단 문장 {x['cited']}/{x['sentences']}",
            flush=True,
        )
(ROOT / "data" / "lg_compare.json").write_text(json.dumps({"lines": lines, "rows": rows}, ensure_ascii=False))
print("저장 → data/lg_compare.json   그래프 화면: uv run python sec14/05_graph_web.py")
