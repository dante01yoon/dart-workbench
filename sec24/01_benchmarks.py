"""24편 ① 공개 벤치마크 비교표 — 각 벤치마크가 무엇을 재고, 어떻게 채점하고, 어디서 한계가 오는지.
숫자는 모두 1차 출처(논문 · 공식 글)에서 확인했다(benchmarks.json의 url · where). API를 부르지 않는다.
사용: uv run python sec24/01_benchmarks.py → http://127.0.0.1:8825
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sec23"))
from page import page, serve

B = json.loads((HERE / "benchmarks.json").read_text())


def html():
    trs = "".join(
        f"<tr><td><b>{r['name']}</b><br><span class=sub>{r['year']}</span></td><td>{r['measures']}</td>"
        f"<td>{r['grading']}</td><td>{r['size']}</td><td>{r['headline']}</td><td>{r['limit']}</td></tr>"
        for r in B["rows"]
    )
    src = "".join(f"<span class=tag>{r['name']} · {r['url']} · {r['where']}</span>" for r in B["rows"])
    return page(
        "공개 벤치마크 비교",
        "<h1>공개 벤치마크는 각각 무엇을 재나</h1>"
        f"<p class=sub>{B['checked']} 1차 출처 확인</p>"
        "<table><tr><th>이름</th><th>무엇을 재나</th><th>채점</th><th>규모</th><th>대표 숫자</th><th>한계</th></tr>"
        f"{trs}</table><h2>출처</h2><div>{src}</div>",
    )


if __name__ == "__main__":
    for r in B["rows"]:
        print(f"{r['name']} — {r['measures']} · 채점: {r['grading'][:34]}…")
    serve(html(), 8825)
