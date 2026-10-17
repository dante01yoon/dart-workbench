"""3편 ④ 도구 수 그래프 — data/tool_count.json을 막대그래프로 보여 준다(표준 라이브러리만).
사용: uv run python sec03/04_graph.py  → http://127.0.0.1:8801"""

import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "tool_count.json"
COLORS = ["#4f7cf0", "#e0a43a"]


def page():
    rows = json.loads(DATA.read_text()) if DATA.exists() else []
    models = list(dict.fromkeys(r["model"] for r in rows))
    configs = list(dict.fromkeys(r["config"] for r in rows))
    by = {(r["model"], r["config"]): r for r in rows}
    top = max((r["prompt_tokens"] for r in rows), default=1)
    groups = ""
    for c in configs:
        bars = ""
        for i, m in enumerate(models):
            r = by.get((m, c))
            if not r:
                continue
            h = r["prompt_tokens"] / top * 520
            bars += (
                f'<div class="col"><span class="v">{r["prompt_tokens"]:,}</span>'
                f'<i style="height:{h:.0f}px;background:{COLORS[i % 2]}"></i>'
                f'<span class="acc">정확도 {r["accuracy"] * 100:.0f}%</span></div>'
            )
        groups += (
            f'<div class="grp"><div class="bars">{bars}</div><div class="lbl">{html.escape(c)}</div></div>'
        )
    legend = "".join(
        f'<span><i style="background:{COLORS[i % 2]}"></i>{html.escape(m)}</span>'
        for i, m in enumerate(models)
    )
    empty = '<p class="empty">아직 기록이 없습니다: uv run python sec03/01_count.py</p>'
    return f"""<!doctype html><meta charset="utf-8"><title>도구 수 그래프</title>
<style>body{{margin:0;background:#111317;color:#e8eaf0;font:24px/1.5 "Apple SD Gothic Neo",system-ui,sans-serif;padding:48px 64px}}
h1{{font-size:40px;margin:0 0 6px}}p{{color:#9aa1b2;margin:0 0 20px}}.legend span{{margin-right:28px}}
.legend i{{display:inline-block;width:16px;height:16px;border-radius:4px;margin-right:8px;vertical-align:-2px}}
.chart{{display:flex;gap:56px;align-items:flex-end;margin-top:36px;border-bottom:1px solid #2c313c;padding:0 12px}}
.grp{{flex:1}}.bars{{display:flex;gap:14px;align-items:flex-end;justify-content:center;height:620px}}
.col{{display:flex;flex-direction:column;align-items:center;width:130px}}.col i{{display:block;width:96px;border-radius:6px 6px 0 0}}
.v{{font-weight:700;margin-bottom:6px}}.acc{{font-size:19px;color:#9aa1b2;margin-top:8px;white-space:nowrap}}
.lbl{{text-align:center;padding:14px 0;font-weight:600;white-space:nowrap}}</style>
<h1>도구 수와 호출 한 번의 입력 토큰</h1><p>질문 20개 × 3번(도구 3개는 답할 수 있는 6문항) · 막대 = 호출 한 번에 모델이 읽는 토큰 · 아래 = 맞는 도구를 고른 비율</p>
<div class="legend">{legend}</div><div class="chart">{groups}</div>{"" if rows else empty}"""


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
    print("도구 수 그래프: http://127.0.0.1:8801")
    HTTPServer(("127.0.0.1", 8801), H).serve_forever()
