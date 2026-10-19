"""26편 과제 3 — 처음 틀어진 단계를 문항 출처별로 나눠 센다(13편부터 보던 문항 · 실행 기록에서 온 문항 · 24편 실패 문항).
사용: uv run python sec26/solutions/a3_matrix_by_source.py
"""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
memos = json.loads((ROOT / "data" / "memos26.json").read_text())
src = {
    json.loads(line)["id"]: json.loads(line).get("source", "")
    for line in (ROOT / "eval" / "questions_v2_locked.jsonl").open()
}


def origin(i):
    if i in ("q32", "q33", "q38", "q50", "q52"):
        return "24편 실패"
    return "13편 문항" if src.get(i) == "13편 시험지" else "실행 기록 · 새 문항"


traces = [json.loads(line) for line in (ROOT / "data" / "traces26.jsonl").open()]
for o in ("13편 문항", "실행 기록 · 새 문항", "24편 실패"):
    ids = [x["id"] for x in traces if origin(x["id"]) == o]
    c = Counter(memos[i]["stage"] for i in ids if i in memos)
    print(
        f"{o:10s} {len(ids):2d}문항 · 메모 {sum(c.values())}개 · "
        + " · ".join(f"{k} {v}" for k, v in c.most_common())
    )
