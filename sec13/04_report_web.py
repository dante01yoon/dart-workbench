"""13편 ④ 인용 배지 보고서 화면 — data/team_eval.json을 읽어 문항마다 보고서 문장 배지(지지 · 부족 · 출처 없음)와
근거 목록(출처 · 인용 · 원문 일치 · 숫자 일치)을 보여 준다. 맨 위는 20문항 루브릭.
사용: uv run python sec13/04_report_web.py → http://127.0.0.1:8813 (?i=문항 번호)"""

import html
import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec12"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec10"))
from verify import numbers_ok
from web import ROOT

BADGE = {"지지": ("#23402f", "#9fe0b5"), "부족": ("#4a3a1c", "#f2c14e"), "출처 없음": ("#4a2323", "#f3a9a9")}
CSS = """body{margin:0;background:#111317;color:#e8eaf0;font:18px/1.55 "Apple SD Gothic Neo",system-ui,sans-serif;padding:24px 40px}
h1{font-size:30px;margin:0 0 10px}select,button{font:inherit;background:#1c1f28;color:#e8eaf0;border:1px solid #39404f;border-radius:10px;padding:6px 12px}
button{background:#4f7cf0;border:0;color:#fff}.rub{display:flex;gap:14px;margin:10px 0 14px;flex-wrap:wrap}
.k{background:#1a1d26;border:1px solid #2c313c;border-radius:12px;padding:8px 16px}.k b{font-size:24px;display:block}
.wrap{display:grid;grid-template-columns:1.1fr 1fr;gap:18px;margin-top:12px}.box{background:#1a1d26;border:1px solid #2c313c;border-radius:14px;padding:14px 18px}
.s{margin:8px 0}.tag{font-size:14px;border-radius:6px;padding:1px 8px;margin-right:8px}.why{color:#c9a85a;font-size:15px;margin:2px 0 0 4px}
.e{border-left:3px solid #2c313c;padding:4px 10px;margin:8px 0;font-size:15px;color:#b8bfcc}.e b{color:#e8eaf0}.ok{color:#9fe0b5}.no{color:#f3a9a9}"""


def rubric(rows):
    sents = [s for r in rows for s in r["report"]]
    qa = [tuple(map(int, r["quote_ok"].split("/"))) for r in rows]
    items = [
        ("정답", f"{sum(r['correct'] for r in rows)}/{len(rows)}"),
        ("출처 단 문장", f"{sum(s['badge'] != '출처 없음' for s in sents)}/{len(sents)}"),
        ("심판 지지", f"{sum(s['badge'] == '지지' for s in sents)}/{len(sents)}"),
        ("인용 원문 일치", f"{sum(a for a, _ in qa)}/{sum(b for _, b in qa)}"),
        ("비용", f"${sum(r['cost'] for r in rows):.3f}"),
    ]
    return '<div class="rub">' + "".join(f'<div class="k">{k}<b>{v}</b></div>' for k, v in items) + "</div>"


def page(i=0):
    rows = json.loads((ROOT / "data" / "team_eval.json").read_text())
    r = rows[i]
    opts = "".join(
        f'<option value="{n}"{" selected" if n == i else ""}>{x["id"]} · {"○" if x["correct"] else "×"} · '
        f"{html.escape(x['q'])}</option>"
        for n, x in enumerate(rows)
    )
    left = ""
    for s in r["report"] or [
        {
            "sentence": "(거절 — 보고서 없음)" if r["refused"] else "(빈 보고서)",
            "cites": [],
            "badge": "출처 없음",
            "reason": "",
        }
    ]:
        bg, fg = BADGE[s["badge"]]
        left += (
            f'<div class="s"><span class="tag" style="background:{bg};color:{fg}">{s["badge"]}</span>'
            f"{html.escape(s['sentence'])} <small>{' '.join(s['cites'])}</small>"
            + (f'<div class="why">↳ {html.escape(s["reason"])}</div>' if s["badge"] == "부족" else "")
            + "</div>"
        )
    right = ""
    for e in r["evidence"]:
        n_ok = numbers_ok(e["claim"], e["quote"])
        right += (
            f'<div class="e"><b>{e["id"]} · {e["kind"]}</b> {html.escape(e["source"][:60])}<br>'
            f"“{html.escape(e['quote'][:160])}”<br>"
            f'<span class="{"ok" if e["verified"] else "no"}">원문 {"일치" if e["verified"] else "없음"}</span> · '
            f'<span class="{"ok" if n_ok else "no"}">숫자 {"일치" if n_ok else "불일치"}</span></div>'
        )
    return f"""<!doctype html><meta charset="utf-8"><title>인용 배지 보고서</title><style>{CSS}</style>
<h1>인용 배지 보고서 · 리서치 팀 20문항</h1>{rubric(rows)}
<form><select name="i">{opts}</select> <button>보기</button></form>
<div class="wrap"><div class="box"><b>보고서</b>{left}</div><div class="box"><b>근거 {len(r["evidence"])}개</b>{right or "<p>없음</p>"}</div></div>"""


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
    print("http://127.0.0.1:8813")
    HTTPServer(("127.0.0.1", 8813), H).serve_forever()
