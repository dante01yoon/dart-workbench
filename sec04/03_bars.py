"""4편 ③ 턴별 컨텍스트 막대 — data/context_runs.json을 방식별·질문별로 보여 준다(표준 라이브러리만).
막대 하나 = 모델 호출 한 번에 읽은 토큰. 오른쪽으로 갈수록 대화가 쌓인다.
사용: uv run python sec04/03_bars.py  → http://127.0.0.1:8802"""

import html
import json
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "context_runs.json"
COLORS = {"A": "#e0605a", "B": "#e0a43a", "C": "#4f7cf0"}


def page():
    runs = json.loads(DATA.read_text()) if DATA.exists() else {}
    top = max((t for r in runs.values() for row in r["rows"] for t in row["calls"]), default=1)
    qids = list(dict.fromkeys(row["id"] for r in runs.values() for row in r["rows"]))
    head = "".join(
        f'<div class="sum"><i style="background:{COLORS.get(k, "#888")}"></i><b>{k} {html.escape(r["label"])}</b>'
        f"<span>통과 {sum(x['ok'] for x in r['rows'])}/{len(r['rows'])} · "
        f"토큰 {sum(sum(x['calls']) for x in r['rows']):,} · ${sum(x['cost'] for x in r['rows']):.3f}</span></div>"
        for k, r in sorted(runs.items())
    )
    grid = ""
    for qid in qids:
        cells = ""
        for k, r in sorted(runs.items()):
            row = next((x for x in r["rows"] if x["id"] == qid), None)
            if not row:
                continue
            bars = "".join(
                f'<i style="height:{max(3, 95 * math.sqrt(t / top)):.0f}px;background:{COLORS.get(k, "#888")}" '
                f'title="{t:,}"><em>{t / 1000:.0f}k</em></i>'
                for t in row["calls"]
            )
            cells += f'<div class="cell"><div class="bars">{bars}</div><div class="mark">{"✅" if row["ok"] else "❌"}</div></div>'
        q = next(x["q"] for r in runs.values() for x in r["rows"] if x["id"] == qid)
        grid += f'<div class="q">{html.escape(q)}</div>{cells}'
    cols = len(runs) or 1
    return f"""<!doctype html><meta charset="utf-8"><title>턴별 컨텍스트</title>
<style>body{{margin:0;background:#111317;color:#e8eaf0;font:22px/1.45 "Apple SD Gothic Neo",system-ui,sans-serif;padding:32px 56px}}
h1{{font-size:36px;margin:0 0 4px}}p{{color:#9aa1b2;margin:0 0 18px}}.head{{display:flex;gap:40px;margin-bottom:18px}}
.sum i{{display:inline-block;width:16px;height:16px;border-radius:4px;margin-right:8px;vertical-align:-2px}}.sum span{{display:block;color:#9aa1b2;font-size:19px}}
.grid{{display:grid;grid-template-columns:420px repeat({cols},1fr);gap:2px 36px;align-items:end}}
.q{{font-size:20px;padding-bottom:26px}}.cell{{border-bottom:1px solid #2c313c;padding-bottom:4px}}
.bars{{display:flex;gap:6px;align-items:flex-end;height:112px}}.bars i{{display:block;width:30px;border-radius:4px 4px 0 0;position:relative}}
.bars em{{position:absolute;bottom:100%;left:50%;transform:translateX(-50%);font-style:normal;font-size:16px;color:#c9cdd6;white-space:nowrap}}
.mark{{font-size:16px}}</style>
<h1>턴별 컨텍스트</h1><p>막대 하나 = 모델 호출 한 번에 읽은 토큰(높이는 제곱근 눈금) · 왼쪽부터 대화 순서</p>
<div class="head">{head}</div><div class="grid">{grid}</div>"""


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
    print("턴별 컨텍스트: http://127.0.0.1:8802")
    HTTPServer(("127.0.0.1", 8802), H).serve_forever()
