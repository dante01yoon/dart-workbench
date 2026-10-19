"""과제 1 풀이: 지도 ⑥에 "성공 1건당 비용"을 채운다 — 문항당 비용이 아니라 맞힌 답 하나를 얻는 데 든 돈과 시간.
사용: uv run python sec23/solutions/a1_cost_per_success.py
"""

import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"
d = json.loads((DATA / "final_eval.json").read_text())  # 22편 최종 성적표(같은 20문항)
for who, rows in (("처음 · 1편 루프", d["first"]), ("지금 · 워크벤치", d["now"])):
    ok = sum(x["correct"] for x in rows)
    cost, sec = sum(x["cost"] for x in rows), sum(x["seconds"] for x in rows)
    print(
        f"{who}: 정답 {ok}/{len(rows)} · 문항당 ${cost / len(rows):.5f} · 성공 1건당 ${cost / ok:.5f} · {sec / ok:.0f}초"
    )
