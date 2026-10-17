"""11편 ④ 비교 화면 — data/rag/frameworks.json을 읽어 직접 · LangChain · LlamaIndex의 recall@5를 막대로,
검색 코드 줄 수와 준비 시간을 표로 보여 준다(표준 라이브러리만). ?set=원래 또는 ?set=말 바꿈
사용: uv run python sec11/04_compare_web.py → http://127.0.0.1:8811"""

import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec07"))
from rag import DIR

IMPLS = ["직접", "LangChain", "LlamaIndex"]
COLOR = {"직접": "#4f7cf0", "LangChain": "#4fb37a", "LlamaIndex": "#e0a43a"}
KINDS = {"keyword": "키워드 BM25", "vector": "벡터", "hybrid": "하이브리드"}
CSS = """body{margin:0;background:#111317;color:#e8eaf0;font:20px/1.5 "Apple SD Gothic Neo",system-ui,sans-serif;padding:28px 48px}
h1{font-size:32px;margin:0 0 6px}.sub{color:#9aa1b2;margin-bottom:18px}a{color:#9aa1b2;margin-right:14px}a.on{color:#e8eaf0;font-weight:700}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}.card{background:#1a1d26;border:1px solid #2c313c;border-radius:14px;padding:16px 20px}
.card h2{font-size:24px;margin:0 0 12px}.row{display:grid;grid-template-columns:120px 1fr 64px;align-items:center;gap:10px;margin:10px 0}
.bar{height:26px;border-radius:6px}.track{background:#23262f;border-radius:6px}.v{text-align:right;font-variant-numeric:tabular-nums}
.warn{color:#e05d5d}table{border-collapse:collapse;margin-top:22px;font-size:19px}td,th{border:1px solid #2c313c;padding:8px 18px;text-align:center}th{background:#1a1d26}"""


def page(sel="원래"):
    d = json.loads((DIR / "frameworks.json").read_text())
    rows = [r for r in d["rows"] if r["set"] == sel]
    tabs = "".join(
        f'<a class="{"on" if s == sel else ""}" href="?set={urllib.parse.quote(s)}">{s} 질문</a>'
        for s in ("원래", "말 바꿈")
    )
    cards = ""
    for kind, name in KINDS.items():
        cards += f'<div class="card"><h2>{name}</h2>'
        for impl in IMPLS:
            r = next(x for x in rows if x["impl"] == impl and x["kind"] == kind)
            v = r["recall@5"]
            cards += (
                f'<div class="row"><span>{impl}</span><div class="track"><div class="bar" '
                f'style="width:{v * 100:.0f}%;background:{COLOR[impl]}"></div></div><span class="v">{v:.3f}</span></div>'
            )
        if kind == "keyword":
            for impl in ("LangChain", "LlamaIndex"):
                r = next(x for x in rows if x["impl"] == f"{impl} 기본 토크나이저")
                cards += (
                    f'<div class="row warn"><span>{impl[:5]}… 기본</span><div class="track"><div class="bar" '
                    f'style="width:{r["recall@5"] * 100:.0f}%;background:#e05d5d"></div></div>'
                    f'<span class="v">{r["recall@5"]:.3f}</span></div>'
                )
        cards += "</div>"
    table = "<table><tr><th></th>" + "".join(f"<th>{i}</th>" for i in IMPLS) + "</tr>"
    table += "<tr><td>검색 코드 줄 수</td>" + "".join(f"<td>{d['lines'][i]}</td>" for i in IMPLS) + "</tr>"
    table += (
        "<tr><td>준비 시간</td><td>-</td>"
        + "".join(f"<td>{d['build'][i]}초</td>" for i in IMPLS[1:])
        + "</tr></table>"
    )
    return f"""<!doctype html><meta charset="utf-8"><title>프레임워크 비교</title><style>{CSS}</style>
<h1>직접 vs LangChain vs LlamaIndex</h1><div class="sub">같은 청크 · 같은 임베딩 · 2025년 38문항 · 회사 필터 · recall@5 &nbsp; {tabs}</div>
<div class="grid">{cards}</div>{table}"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        p = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        b = page(p.get("set", ["원래"])[0]).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("http://127.0.0.1:8811")
    HTTPServer(("127.0.0.1", 8811), H).serve_forever()
