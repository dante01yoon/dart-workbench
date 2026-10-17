"""14편 ① 그래프 모양을 그리고, 질문 하나를 단계별로 흘려 본다(사람 승인은 자동 통과).
사용: uv run --group frameworks python sec14/01_graph.py ["질문"]"""

import os
import time

os.environ["AUTO_APPROVE"] = "1"
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import build

app = build()
print(app.get_graph().draw_mermaid())
q = " ".join(sys.argv[1:]) or "현대자동차의 2025년 실적과 최근 관세 관련 뉴스를 같이 정리해 줘"
print(f"질문: {q}\n")
t0, report = time.time(), []
for step in app.stream({"question": q}, stream_mode="updates"):
    for node, out in step.items():
        what = ""
        if node == "planner":
            what = " · ".join(f"{t['worker']}({t.get('corp') or '-'})" for t in out.get("tasks", []))
        elif node == "worker":
            what = f"근거 {len(out['evidence'])}개"
        elif node == "writer":
            report = out["report"]
            what = f"보고서 {len(report)}문장"
        print(f"  {time.time() - t0:5.1f}초  {node:8s} {what}", flush=True)
print()
for s in report:
    print(f"  {'●' if s['cites'] else '○'} {s['sentence']} {s['cites']}")
