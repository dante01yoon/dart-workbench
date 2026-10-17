"""12편 ③ 타임라인 화면 — data/team_compare.json을 읽어 질문마다 단일 · 순차 팀 · 병렬 팀의 시간 막대와 비교표를 보여 준다.
사용: uv run python sec12/03_timeline_web.py → http://127.0.0.1:8812 (?i=질문 번호)"""

import html
import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec07"))
from rag import ROOT

COLOR = {
    "planner": "#9a7cf0",
    "writer": "#e0a43a",
    "filings": "#4f7cf0",
    "search_report": "#4f7cf0",
    "financials": "#4fb37a",
    "key_accounts": "#4fb37a",
    "news": "#e05d8a",
}
NAME = {
    "planner": "계획",
    "writer": "작성",
    "filings": "공시",
    "search_report": "공시",
    "financials": "재무",
    "key_accounts": "재무",
    "news": "뉴스",
}
CSS = """body{margin:0;background:#111317;color:#e8eaf0;font:19px/1.5 "Apple SD Gothic Neo",system-ui,sans-serif;padding:26px 44px}
h1{font-size:30px;margin:0 0 4px}.q{color:#9aa1b2;margin-bottom:14px}a{color:#9aa1b2;margin-right:12px}a.on{color:#e8eaf0;font-weight:700}
.lane{background:#1a1d26;border:1px solid #2c313c;border-radius:14px;padding:12px 18px;margin:10px 0}.lane h2{font-size:21px;margin:0 0 8px}
.track{position:relative;height:{H}px}.seg{position:absolute;height:22px;border-radius:5px;font-size:14px;color:#111;padding:0 6px;
white-space:nowrap;overflow:hidden;line-height:22px}.axis{color:#6b7280;font-size:14px}
table{border-collapse:collapse;margin-top:14px;font-size:18px}td,th{border:1px solid #2c313c;padding:6px 16px;text-align:center}th{background:#1a1d26}"""


def lane(x, scale):
    segs, rows = x["timeline"], {}
    for s in segs:  # 겹치는 막대는 줄을 바꿔 쌓는다
        r = 0
        while any(not (s["start"] >= e or s["end"] <= b) for b, e in rows.get(r, [])):
            r += 1
        rows.setdefault(r, []).append((s["start"], s["end"]))
        s["row"] = r
    h = (max(s["row"] for s in segs) + 1) * 26 if segs else 26
    out = f'<div class="lane"><h2>{x["mode"]} · {x["seconds"]:.0f}초 · ${x["cost"]:.4f}</h2><div class="track" style="height:{h}px">'
    for s in segs:
        w = max(0.4, (s["end"] - s["start"]) * scale)
        label = NAME.get(s["who"], s["who"]) + (f" {s['corp']}" if s.get("corp") else "")
        out += (
            f'<div class="seg" style="left:{s["start"] * scale:.1f}%;width:{w:.1f}%;top:{s["row"] * 26}px;'
            f'background:{COLOR.get(s["who"], "#9aa1b2")}" title="{html.escape(s.get("query", ""))}">{html.escape(label)}</div>'
        )
    return out + "</div></div>"


def page(i=0):
    rows = json.loads((ROOT / "data" / "team_compare.json").read_text())
    qs = list(dict.fromkeys(r["q"] for r in rows))
    mine = [r for r in rows if r["q"] == qs[i]]
    scale = 100 / max(r["seconds"] for r in mine)
    tabs = "".join(
        f'<a class="{"on" if n == i else ""}" href="?i={n}">질문 {n + 1}</a>' for n in range(len(qs))
    )
    table = "<table><tr><th></th><th>시간</th><th>비용</th><th>작업 · 도구 호출</th><th>출처 단 문장</th><th>인용 원문 일치</th></tr>"
    for r in mine:
        table += (
            f"<tr><td>{r['mode']}</td><td>{r['seconds']:.0f}초</td><td>${r['cost']:.4f}</td><td>{r['work']}</td>"
            f"<td>{r['cited']}</td><td>{r.get('quote_ok') or '-'}</td></tr>"
        )
    return f"""<!doctype html><meta charset="utf-8"><title>리서치 팀 타임라인</title><style>{CSS.replace("{H}", "26")}</style>
<h1>단일 에이전트 vs 순차 팀 vs 병렬 팀</h1><div class="q">{tabs} &nbsp; {html.escape(qs[i])}</div>
{"".join(lane(r, scale) for r in mine)}{table}"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        p = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        b = page(int(p.get("i", ["0"])[0])).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("http://127.0.0.1:8812")
    HTTPServer(("127.0.0.1", 8812), H).serve_forever()
