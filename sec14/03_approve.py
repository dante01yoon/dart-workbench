"""14편 ③ 사람 승인: 계획을 보고 뺄 작업을 고른 뒤 이어서 돈다(interrupt → Command(resume=...)).
사용: uv run --group frameworks python sec14/03_approve.py ["질문"]"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import build
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

app = build(InMemorySaver())
cfg = {"configurable": {"thread_id": "approve-1"}}
q = " ".join(sys.argv[1:]) or "삼성전자와 SK하이닉스의 2025년 실적과 위험 요인을 비교해 줘"
out = app.invoke({"question": q}, cfg)
for it in out.get("__interrupt__", []):
    print("계획을 확인해 주세요:")
    for t in it.value["tasks"]:
        print(f"  {t['id']}  {t['worker']:10s} {(t.get('corp') or '-'):6s} {t['query']}")
answer = input("뺄 작업(번호 t2,t4 또는 종류 filings · news · 없으면 엔터): ").replace(" ", "")
tasks = out["__interrupt__"][0].value["tasks"] if out.get("__interrupt__") else []
drop = [t["id"] for t in tasks if t["id"] in answer.split(",") or t["worker"] in answer.split(",")]
out = app.invoke(Command(resume=drop), cfg)
print(f"\n뺀 작업 {drop or '없음'} → 남은 작업 {len(out['tasks'])}개 · 근거 {len(out['evidence'])}개")
for s in out["report"]:
    print(f"  {'●' if s['cites'] else '○'} {s['sentence']}")
