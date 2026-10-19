"""과제 2 풀이: 틀린 문항을 직접 열어 "에이전트가 틀렸나, 채점기가 틀렸나"를 나눈다. 정답 키와 보고서 문장을 나란히 찍는다. API 호출 없음.
사용: uv run python sec24/solutions/a2_open_failures.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QS = {json.loads(line)["id"]: json.loads(line) for line in (ROOT / "eval" / "questions.jsonl").open()}
KEYS = json.loads((ROOT / "eval" / "answer_keys.json").read_text())
d = json.loads((ROOT / "data" / "heldout24.json").read_text())
for split in ("dev", "new"):
    for x in d[split]:
        if x["correct"]:
            continue
        print(f"[{split}] {x['id']} {QS[x['id']]['q']}\n  정답 키: {KEYS[x['id']]}")
        for s in x["report"][:4]:
            print(f"  - {s['sentence']}")
        if not x["report"]:
            print("  - (보고서 없음: 거절 또는 빈 답)")
