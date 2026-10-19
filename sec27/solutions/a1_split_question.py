"""27편 과제 1 — 25편에서 "기준이 사람마다 다르다"며 뺀 질문(삼성전자 자사주 정책 정리)을 예/아니오 기준으로 쪼갠다.
정책 정리처럼 열린 질문도, 공시에 있어야 할 사실을 항목별로 나누면 하나씩 예/아니오로 잴 수 있다.
26편 기록에서 같은 종류의 답(n11 카카오 자사주 소각)에 기준을 적용해 본다.
사용: uv run python sec27/solutions/a1_split_question.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CHECKS = [  # (기준, 답에 있어야 할 낱말 중 하나)
    ("소각 여부를 답했나?", ("소각",)),
    ("소각 수량(주)을 공시 숫자로 답했나?", ("2,202,644", "220만 2,644")),
    ("취득(매입) 여부를 답했나?", ("취득", "매입")),
    ("다음 해 소각 결의(공시)를 짚었나?", ("1,420,723",)),
    ("근거가 공시인가(사업보고서 인용)?", None),
]
x = next(x for x in map(json.loads, (ROOT / "data" / "traces26.jsonl").open()) if x["id"] == "n11")
text = " ".join(s["sentence"] for s in x["report"])
ev = {e["id"]: e for e in x["evidence"]}
for q, words in CHECKS:
    if words:
        ok = any(w.replace(" ", "") in text.replace(" ", "") for w in words)
    else:
        ok = all(any("사업보고서" in ev[c]["source"] for c in s["cites"]) for s in x["report"])
    print(f"{'예  ' if ok else '아니오'} {q}")
