"""26편 과제 1 — 맞았다고 채점된 답 중 먼저 읽을 것을 신호로 고른다(모델 호출 없음).
신호: ① 질문이 뉴스를 묻지 않았는데 뉴스를 근거로 씀 ② 심판이 '부족' · '출처 없음'이라고 한 문장이 있음 ③ 거절 문항인데 보고서가 있음
사용: uv run python sec26/solutions/a1_suspicious_passes.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
memos = json.loads((ROOT / "data" / "memos26.json").read_text())
picked = []
for x in map(json.loads, (ROOT / "data" / "traces26.jsonl").open()):
    if not x["correct"]:
        continue
    news = {
        e["id"] for e in x["evidence"] if "사업보고서" not in e["source"] and "재무 API" not in e["source"]
    }
    why = []
    if "뉴스" not in x["q"] and any(c in news for s in x["report"] for c in s["cites"]):
        why.append("뉴스 근거")
    if any(s["badge"] != "지지" for s in x["report"]):
        why.append("심판 부족")
    if x["keys"] == "refuse" and x["report"]:
        why.append("거절 문항에 보고서")
    if why:
        picked.append(x["id"])
        print(f"{x['id']} {' · '.join(why):20s} 메모: {memos.get(x['id'], {}).get('memo', '-')[:50]}")
total = sum(json.loads(line)["correct"] for line in (ROOT / "data" / "traces26.jsonl").open())
print(
    f"\n맞았다는 답 {total}개 중 신호가 있는 답 {len(picked)}개 · 그중 메모가 문제를 찾은 답: {[i for i in picked if i in memos]}"
)
