"""23편 ② 미국 채용 공고 12개 × 역량 — 공고마다 손으로 표시한 라벨(jobs.json)을 세어 빈도표와 표 화면을 만든다.
라벨은 공고의 역할 설명 · 자격 요건만 읽고 붙였다(회사 소개 문단 제외). API를 부르지 않는다.
사용: uv run python sec23/02_job_skills.py → 터미널 빈도표 + http://127.0.0.1:8824
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from page import page, serve

J = json.loads((HERE / "jobs.json").read_text())


def counts(jobs=None):
    jobs = jobs or J["jobs"]
    return {s["id"]: sum(s["id"] in j["skills"] for j in jobs) for s in J["skills"]}


def html():
    n = counts()
    head = "".join(f"<th title='{j['company']} · {j['title']}'>{j['id']}</th>" for j in J["jobs"])
    rows = ""
    for s in sorted(J["skills"], key=lambda s: -n[s["id"]]):
        dots = "".join(
            f"<td><span class='dot{' on' if s['id'] in j['skills'] else ''}'></span></td>" for j in J["jobs"]
        )
        rows += f"<tr><td>{s['name']}</td>{dots}<td class=num><b>{n[s['id']]}</b>/12</td><td>{s['lesson']}</td></tr>"
    legend = "".join(f"<span class=tag>{j['id']} {j['company']} · {j['title']}</span>" for j in J["jobs"])
    return page(
        "공고 12개 × 역량",
        "<h1>미국 AI 평가 공고 12개 × 역량</h1>"
        f"<p class=sub>{J['checked']} 확인 · {J['note']}</p>"
        f"<table><tr><th>역량</th>{head}<th>공고 수</th><th>다루는 편</th></tr>{rows}</table>"
        f"<h2>공고</h2><div>{legend}</div>",
    )


if __name__ == "__main__":
    n = counts()
    for s in sorted(J["skills"], key=lambda s: -n[s["id"]]):
        print(f"{n[s['id']]:>2}/12 {'█' * n[s['id']]:<12} {s['name']} → {s['lesson']}")
    serve(html(), 8824)
