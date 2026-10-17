"""14편 ⑤ 그래프 화면 — 12편 팀을 옮긴 LangGraph 그래프 모양과, data/lg_compare.json의 직접 vs LangGraph 비교표.
사용: uv run python sec14/05_graph_web.py → http://127.0.0.1:8814"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec07"))
from rag import ROOT

CSS = """body{margin:0;background:#111317;color:#e8eaf0;font:19px/1.5 "Apple SD Gothic Neo",system-ui,sans-serif;padding:26px 44px}
h1{font-size:30px;margin:0 0 14px}.flow{display:flex;align-items:center;gap:14px;margin:8px 0 22px}
.n{background:#1a1d26;border:2px solid #39404f;border-radius:14px;padding:12px 18px;text-align:center;min-width:120px}
.n b{display:block;font-size:21px}.n small{color:#9aa1b2}.ar{color:#6b7280;font-size:26px}
.par{display:flex;flex-direction:column;gap:8px}.w{border-color:#4f7cf0}.h{border-color:#e0a43a}.p{border-color:#9a7cf0}.wr{border-color:#4fb37a}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:22px}table{border-collapse:collapse;width:100%;font-size:18px}
td,th{border:1px solid #2c313c;padding:7px 12px;text-align:center}th{background:#1a1d26}td.l{text-align:left}"""


def page():
    d = json.loads((ROOT / "data" / "lg_compare.json").read_text())
    flow = """<div class="flow"><div class="n p"><b>planner</b><small>작업 나누기</small></div><span class="ar">→</span>
<div class="n h"><b>approve</b><small>사람 승인 · interrupt</small></div><span class="ar">→</span>
<div class="par"><div class="n w"><b>worker</b><small>공시</small></div><div class="n w"><b>worker</b><small>재무</small></div>
<div class="n w"><b>worker</b><small>뉴스</small></div></div><span class="ar">→</span>
<div class="n wr"><b>writer</b><small>보고서</small></div></div>"""
    feat = [
        ("흐름 코드 줄 수", d["lines"]["직접"], d["lines"]["LangGraph"]),
        ("병렬 실행", "ThreadPoolExecutor", "Send(작업마다)"),
        ("죽었다가 이어서 돌기", "없음 · 처음부터", "체크포인트 · thread_id"),
        ("사람 승인", "없음", "interrupt · Command(resume)"),
        ("그래프 그림", "없음", "draw_mermaid()"),
    ]
    t1 = (
        "<table><tr><th></th><th>직접(12편)</th><th>LangGraph</th></tr>"
        + "".join(f'<tr><td class="l">{a}</td><td>{b}</td><td>{c}</td></tr>' for a, b, c in feat)
        + "</table>"
    )
    t2 = "<table><tr><th>질문</th><th>구현</th><th>시간</th><th>근거</th><th>출처 단 문장</th></tr>"
    for r in d["rows"]:
        t2 += (
            f'<tr><td class="l">{r["q"][:14]}…</td><td>{r["impl"]}</td><td>{r["seconds"]:.0f}초</td>'
            f"<td>{r['evidence']}</td><td>{r['cited']}/{r['sentences']}</td></tr>"
        )
    return f"""<!doctype html><meta charset="utf-8"><title>LangGraph 그래프</title><style>{CSS}</style>
<h1>리서치 팀 → LangGraph 상태 그래프</h1>{flow}<div class="grid">{t1}{t2}</table></div>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        b = page().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("http://127.0.0.1:8814")
    HTTPServer(("127.0.0.1", 8814), H).serve_forever()
