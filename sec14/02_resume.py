"""14편 ② 체크포인트로 이어서 돌기: 뉴스 워커를 일부러 죽인 뒤, 같은 thread_id로 다시 실행하면 어디부터 도는지 본다.
상태는 data/lg_checkpoints.sqlite에 저장된다.
사용: uv run --group frameworks python sec14/02_resume.py"""

import os
import sqlite3

os.environ["AUTO_APPROVE"] = "1"
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import TEAM, build
from langgraph.checkpoint.sqlite import SqliteSaver
from web import ROOT

ran = []
for name in ("w_filings", "w_news", "w_financials"):  # 워커가 실제로 불린 횟수를 센다
    orig = getattr(TEAM, name)
    setattr(TEAM, name, lambda t, f=orig, n=name: (ran.append(f"{n[2:]}({t.get('corp') or '-'})"), f(t))[1])

db = ROOT / "data" / "lg_checkpoints.sqlite"
db.unlink(missing_ok=True)
app = build(SqliteSaver(sqlite3.connect(db, check_same_thread=False)))
cfg = {"configurable": {"thread_id": "hyundai-1"}}
q = "현대자동차의 2025년 실적과 최근 관세 관련 뉴스를 같이 정리해 줘"

print("① 첫 실행: 뉴스 워커가 죽는다")
os.environ["CRASH"] = "news"
try:
    app.invoke({"question": q}, cfg)
except RuntimeError as e:
    print(f"  오류: {e}")
print(f"  실제로 돈 워커: {', '.join(ran) or '없음'}")
snap = app.get_state(cfg)
print(f"  저장된 상태: 다음 단계 {list(snap.next)} · 작업 {len(snap.values.get('tasks', []))}개")

print("\n② 같은 thread_id로 다시 실행: 입력 없이 이어서")
del os.environ["CRASH"]
ran.clear()
out = app.invoke(None, cfg)
print(f"  실제로 돈 워커: {', '.join(ran) or '없음'}")
print(f"  근거 {len(out['evidence'])}개 · 보고서 {len(out['report'])}문장")
for s in out["report"]:
    print(f"  {'●' if s['cites'] else '○'} {s['sentence']}")
