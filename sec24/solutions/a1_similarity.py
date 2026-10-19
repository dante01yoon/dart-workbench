"""과제 1 풀이: 처음 보는 20문항을 "개발 문항과 글자가 많이 닮은 것(유사도 0.5 이상)"과 "덜 닮은 것"으로 나눠 정답률을 비교한다.
닮은 문항에서만 잘 맞히면 템플릿을 외운 신호, 차이가 없으면 그 신호가 없다. API 호출 없음.
사용: uv run python sec24/solutions/a1_similarity.py
"""

import json
from pathlib import Path

d = json.loads((Path(__file__).resolve().parents[2] / "data" / "heldout24.json").read_text())
for name, rows in (
    ("닮음(0.5 이상)", [x for x in d["new"] if x["sim"] >= 0.5]),
    ("덜 닮음", [x for x in d["new"] if x["sim"] < 0.5]),
):
    ok = sum(x["correct"] for x in rows)
    print(f"{name}: {ok}/{len(rows)} · " + " ".join(f"{x['id']}({x['sim']})" for x in rows))
