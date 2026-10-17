"""6편 ③ 메인 vs 서브 토큰 막대 — data/subagent_runs.json을 그린다(표준 라이브러리만).
막대 하나 = 모델 호출 한 번에 보낸 입력 토큰. 파랑은 메인 대화, 주황은 서브에이전트 대화.
사용: uv run python sec06/03_bars.py  → http://127.0.0.1:8804"""

import html
import json
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "subagent_runs.json"
LABEL = {"solo": "혼자 (메인이 도구를 직접)", "team": "서브에이전트에게 맡기기"}
MAIN, SUB = "#4f7cf0", "#e0a43a"


def bars(calls, color, top):
    return "".join(
        f'<i style="height:{max(3, 260 * math.sqrt(t / top)):.0f}px;background:{color}" title="{t:,}"><em>{t / 1000:.1f}k</em></i>'
        for t in calls
    )


def page():
    runs = json.loads(DATA.read_text()) if DATA.exists() else []
    top = max(
        [t for r in runs for t in r["main"]] + [t for r in runs for s in r["subs"] for t in s["calls"]] + [1]
    )
    rows = ""
    for r in runs:
        sub_total = sum(sum(s["calls"]) for s in r["subs"])
        groups = f'<div class="g"><b>메인</b><div class="bars">{bars(r["main"], MAIN, top)}</div></div>'
        for s in r["subs"]:
            groups += f'<div class="g"><b>서브 · {html.escape(s["corp"])}</b><div class="bars">{bars(s["calls"], SUB, top)}</div></div>'
        rows += (
            f'<div class="row"><h2>{LABEL[r["mode"]]}</h2><p>주당배당금 {r["ok"]}/4 · 메인 입력 {sum(r["main"]):,} (최대 {max(r["main"]):,}) · '
            f'서브 입력 {sub_total:,} · 합계 {sum(r["main"]) + sub_total:,} · ${r["cost"]:.3f}</p><div class="gs">{groups}</div></div>'
        )
    return f"""<!doctype html><meta charset="utf-8"><title>메인 vs 서브 토큰</title>
<style>body{{margin:0;background:#111317;color:#e8eaf0;font:22px/1.45 "Apple SD Gothic Neo",system-ui,sans-serif;padding:32px 56px}}
h1{{font-size:36px;margin:0 0 4px}}h2{{font-size:28px;margin:0}}p{{color:#9aa1b2;margin:4px 0 12px}}
.row{{border-bottom:1px solid #2c313c;padding:18px 0}}.gs{{display:flex;gap:44px;align-items:flex-end}}
.g b{{display:block;font-size:18px;color:#c9cdd8;margin-top:6px;order:2}}.g{{display:flex;flex-direction:column-reverse}}
.bars{{display:flex;gap:6px;align-items:flex-end;height:300px}}.bars i{{width:34px;border-radius:4px 4px 0 0;position:relative;display:block}}
.bars em{{position:absolute;top:-24px;left:50%;transform:translateX(-50%);font-size:15px;color:#c9cdd8;font-style:normal;white-space:nowrap}}</style>
<h1>메인 vs 서브 토큰</h1><p>막대 하나 = 모델 호출 한 번에 보낸 입력 토큰(높이는 제곱근 눈금) · <span style="color:{MAIN}">■ 메인</span> <span style="color:{SUB}">■ 서브</span></p>{rows}"""


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
    print("http://127.0.0.1:8804")
    HTTPServer(("127.0.0.1", 8804), H).serve_forever()
