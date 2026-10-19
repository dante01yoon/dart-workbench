"""33편 과제 3 — PR 1차(앞 두 문장만)를 Langfuse에 두 번째 실행으로 올리고, main과 문항별로 비교한다.
CI 관문이 잡은 5문항이 Langfuse 비교에서도 그대로 보이나? 모델 호출 0.
사용: uv run --with "langfuse>=2.60,<3" python sec33/solutions/a3_langfuse_compare.py  (04_langfuse.py를 먼저 돌린다)"""

import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from langfuse import Langfuse
from regress import runs, score

HOST = os.environ.setdefault("LANGFUSE_HOST", "http://127.0.0.1:3300")
RUN, DS = "pr-1차", "dart-dev-v2"
xs = runs()
make = lambda r, e: " ".join(r[:2])
ok = score(xs, make)
lf = Langfuse()
for item in lf.get_dataset(DS).items:
    x = next(r for r in xs if r["id"] == item.id)
    t = lf.trace(
        id=f"{RUN}-{x['id']}", name="dart-research", input=x["q"], output=make(x["report"], x["evidence"])
    )
    t.score(id=f"{RUN}-{x['id']}-correct", name="correct", value=float(ok[x["id"]]))
    item.link(t, run_name=RUN)
lf.flush()


def get(path):
    auth = base64.b64encode(
        f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()
    ).decode()
    return json.load(
        urllib.request.urlopen(
            urllib.request.Request(HOST + path, headers={"Authorization": "Basic " + auth})
        )
    )


scores = {}
for page in range(1, 10):
    data = get(f"/api/public/scores?name=correct&limit=100&page={page}")["data"]
    scores |= {s["traceId"]: s["value"] for s in data}
    if len(data) < 100:
        break
reg = {x["id"] for x in xs if x["split"] == "regression"}
diff = [i for i in (x["id"] for x in xs) if scores.get(f"main-{i}") != scores.get(f"{RUN}-{i}")]
print(
    f"Langfuse 실행 main vs {RUN}: 평균 {sum(scores[f'main-{x["id"]}'] for x in xs) / len(xs):.3f} → {sum(scores[f'{RUN}-{x["id"]}'] for x in xs) / len(xs):.3f}"
)
print(f"  점수가 달라진 문항 {len(diff)}개: {' '.join(diff)} (회귀 세트 {sum(i in reg for i in diff)}개)")
