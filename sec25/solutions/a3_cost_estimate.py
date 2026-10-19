"""과제 3 풀이: 시험지 v2 전체를 워크벤치로 한 번 돌리면 얼마 · 몇 분 걸릴지, 24편 실행 기록(같은 날 40문항)으로 미리 계산한다.
유형별 평균을 쓰고, 기록에 없는 유형(보고서형 · 함정)은 전체 평균으로 둔다. 4개씩 동시에 돌린다고 본다. API 호출 없음.
사용: uv run python sec25/solutions/a3_cost_estimate.py
"""

import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QS = {json.loads(line)["id"]: json.loads(line) for line in (ROOT / "eval" / "questions.jsonl").open()}
d = json.loads((ROOT / "data" / "heldout24.json").read_text())
runs = d["dev"] + d["new"]
by = {}
for x in runs:
    by.setdefault(QS[x["id"]]["type"], []).append(x)
avg = {
    t: (statistics.mean(x["cost"] for x in r), statistics.mean(x["seconds"] for x in r))
    for t, r in by.items()
}
allc, alls = statistics.mean(x["cost"] for x in runs), statistics.mean(x["seconds"] for x in runs)
v2 = Counter(json.loads(line)["type"] for line in (ROOT / "eval" / "questions_v2.jsonl").open())
cost = sum(n * avg.get(t, (allc, alls))[0] for t, n in v2.items())
secs = sum(n * avg.get(t, (allc, alls))[1] for t, n in v2.items())
for t, n in v2.most_common():
    c, s = avg.get(t, (allc, alls))
    print(f"{t:<14}{n:>3}문항 · 문항당 ${c:.4f} · {s:.0f}초{'' if t in avg else ' (기록 없음 → 전체 평균)'}")
print(f"v2 {sum(v2.values())}문항 한 번 = 약 ${cost:.2f} · 4개 동시면 약 {secs / 4 / 60:.0f}분")
