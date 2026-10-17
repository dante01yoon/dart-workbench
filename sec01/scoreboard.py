"""1편 ④ 성적표 웹 화면 — data/scorecard.jsonl을 표로 보여 준다(표준 라이브러리만).
사용: uv run python sec01/scoreboard.py  → http://127.0.0.1:8800"""

import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCORECARD = Path(__file__).resolve().parent.parent / "data" / "scorecard.jsonl"
COLS = [
    ("name", "실행"),
    ("pass_rate", "통과율"),
    ("n", "문항"),
    ("tokens", "토큰"),
    ("cost_per_q", "$/문항"),
    ("p50_s", "p50 지연"),
    ("p95_s", "p95 지연"),
    ("date", "시각"),
]


def page():
    rows = (
        [json.loads(l) for l in SCORECARD.read_text(encoding="utf-8").splitlines() if l.strip()]
        if SCORECARD.exists()
        else []
    )
    tr = ""
    for r in rows:
        cells = ""
        for k, _ in COLS:
            v = r.get(k, "")
            if k == "pass_rate":
                v = f'<div class="bar"><i style="width:{v * 100:.0f}%"></i></div><b>{v * 100:.0f}%</b>'
            elif k == "tokens":
                v = f"{v:,}"
            elif k == "cost_per_q":
                v = f"${v:.4f}"
            elif k in ("p50_s", "p95_s"):
                v = f"{v}s"
            else:
                v = html.escape(str(v))
            cells += f"<td>{v}</td>"
        tr += f"<tr>{cells}</tr>"
    head = "".join(f"<th>{t}</th>" for _, t in COLS)
    return f"""<!doctype html><meta charset="utf-8"><title>성적표</title>
<style>body{{margin:0;background:#111317;color:#e8eaf0;font:20px/1.5 "Apple SD Gothic Neo",system-ui,sans-serif;padding:48px 64px}}
h1{{font-size:34px;margin:0 0 6px}}p{{color:#9aa1b2;margin:0 0 28px}}table{{border-collapse:collapse;width:100%}}
th{{text-align:left;color:#9aa1b2;font-weight:600;padding:12px 14px;border-bottom:1px solid #2c313c}}
td{{padding:16px 14px;border-bottom:1px solid #2c313c}}th,td{{white-space:nowrap}}.bar{{display:inline-block;width:140px;height:12px;background:#232733;border-radius:6px;margin-right:10px;vertical-align:middle}}
.bar i{{display:block;height:12px;background:#4f7cf0;border-radius:6px}}</style>
<h1>성적표</h1><p>같은 문제 세트로 바꿀 때마다 한 줄씩 — 통과율 · 토큰 · 문항당 비용 · 지연</p>
<table><tr>{head}</tr>{tr or '<tr><td colspan="8">아직 기록이 없습니다: uv run python sec01/03_harness.py</td></tr>'}</table>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body = page().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("성적표: http://127.0.0.1:8800")
    HTTPServer(("127.0.0.1", 8800), H).serve_forever()
