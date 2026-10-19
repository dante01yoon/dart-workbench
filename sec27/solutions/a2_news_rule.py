"""27편 과제 2 — 기준 R7 "질문이 뉴스를 묻지 않았다면 뉴스를 근거로 쓰지 않았나?"를 더하면 몇 문항이 바뀌나.
사용: uv run python sec27/solutions/a2_news_rule.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
rows = []
for x in map(json.loads, (ROOT / "data" / "traces26.jsonl").open()):
    news = {
        e["id"] for e in x["evidence"] if "사업보고서" not in e["source"] and "재무 API" not in e["source"]
    }
    used = sorted({c for s in x["report"] for c in s["cites"] if c in news})
    if used:
        rows.append((x["id"], "뉴스" in x["q"], x["correct"], len(used)))
print(f"뉴스를 근거로 쓴 답 {len(rows)}개 · 그중 질문이 뉴스를 물은 것 {sum(r[1] for r in rows)}개")
for qid, asked, correct, n in rows:
    print(
        f"  {qid} 뉴스 근거 {n}개 · 질문에 '뉴스' {'있음' if asked else '없음'} · 22편 채점기 {'✅' if correct else '❌'}"
    )
bad = [r for r in rows if not r[1]]
print(f"R7을 더하면 아니오: {len(bad)}개 — 그중 지금 정답 처리된 답 {sum(r[2] for r in bad)}개")
