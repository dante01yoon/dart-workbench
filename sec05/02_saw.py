"""5편 ② 톱니 그래프 — data/long_task.json의 턴별 입력 토큰을 전략별 선으로 그린다(표준 라이브러리만).
점 하나 = 모델 호출 한 번에 보낸 입력 토큰. 그대로 두면 계속 오르고, 지우기·요약은 톱니처럼 내려간다.
사용: uv run python sec05/02_saw.py  → http://127.0.0.1:8803"""

import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "long_task.json"
COLORS = {"none": "#e0605a", "clear": "#e0a43a", "compact": "#4fb37a", "compact+todo": "#4f7cf0"}
LABELS = {
    "none": "그대로",
    "clear": "지우기 + 메모",
    "compact": "요약 압축",
    "compact+todo": "요약 + 할 일 목록",
}
W, H, PAD = 1500, 620, 70


def page():
    runs = json.loads(DATA.read_text()) if DATA.exists() else []
    top = max((t for r in runs for t in r["curve"]), default=1)
    turns = max((len(r["curve"]) for r in runs), default=1)

    def xy(i, t):
        x = PAD + (W - 2 * PAD) * i / max(1, turns - 1)
        y = H - PAD - (H - 2 * PAD) * t / top
        return f"{x:.0f},{y:.0f}"

    lines = "".join(
        f'<polyline fill="none" stroke="{COLORS.get(r["strategy"], "#888")}" stroke-width="4" '
        f'points="{" ".join(xy(i, t) for i, t in enumerate(r["curve"]))}"/>'
        for r in runs
    )
    grid = "".join(
        f'<line x1="{PAD}" x2="{W - PAD}" y1="{y}" y2="{y}" stroke="#2c313c"/>'
        f'<text x="{PAD - 10}" y="{y + 6}" text-anchor="end">{v / 1000:.0f}k</text>'
        for v in range(0, int(top) + 1, max(1000, int(top / 5 // 1000 * 1000) or 1000))
        for y in [H - PAD - (H - 2 * PAD) * v / top]
    )
    head = "".join(
        f'<div class="sum"><i style="background:{COLORS.get(r["strategy"], "#888")}"></i>'
        f"<b>{html.escape(LABELS.get(r['strategy'], r['strategy']))}</b>"
        f"<span>정답 {r['cells']}/{r['of']} · 턴 {r['turns']} · 총 입력 {r['total_prompt_tokens']:,} · "
        f"최대 {r['peak_prompt_tokens']:,} · ${r['cost']:.3f}</span></div>"
        for r in runs
    )
    return f"""<!doctype html><meta charset="utf-8"><title>톱니 그래프</title>
<style>body{{margin:0;background:#111317;color:#e8eaf0;font:22px/1.45 "Apple SD Gothic Neo",system-ui,sans-serif;padding:32px 56px}}
h1{{font-size:36px;margin:0 0 4px}}p{{color:#9aa1b2;margin:0 0 18px}}.head{{display:grid;grid-template-columns:1fr 1fr;gap:10px 40px;margin-bottom:12px}}
.sum i{{display:inline-block;width:16px;height:16px;border-radius:4px;margin-right:8px;vertical-align:-2px}}.sum span{{display:block;color:#9aa1b2;font-size:19px}}
svg text{{fill:#9aa1b2;font-size:17px}}</style>
<h1>턴별 입력 토큰</h1><p>점 하나 = 모델 호출 한 번에 보낸 입력 토큰 · 왼쪽부터 대화 순서</p>
<div class="head">{head}</div>
<svg width="{W}" height="{H}">{grid}{lines}
<text x="{W / 2}" y="{H - 20}" text-anchor="middle">턴</text></svg>"""


class H_(BaseHTTPRequestHandler):
    def do_GET(self):
        body = page().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("톱니 그래프: http://127.0.0.1:8803")
    HTTPServer(("127.0.0.1", 8803), H_).serve_forever()
