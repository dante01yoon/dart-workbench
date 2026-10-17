"""8편 ③ 순위 디버그 화면 — data/rag/compare.json을 읽어, 문항마다 네 방식의 상위 10개를 나란히 보여 준다(표준 라이브러리만).
정답 조각은 ✅. 어느 방식이 몇 위에 정답을 올렸는지, 놓친 방식은 무엇을 1위로 올렸는지 한눈에 본다.
사용: uv run python sec08/03_rank_web.py → http://127.0.0.1:8808"""

import html
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from search import DIR, eval_questions, is_gold, load_store

CHUNKS, _ = load_store()
QS = eval_questions()
NAMES = {"keyword": "키워드 BM25", "vector": "벡터", "hybrid": "하이브리드 RRF", "rerank": "재정렬"}
CSS = """body{margin:0;background:#111317;color:#e8eaf0;font:19px/1.5 "Apple SD Gothic Neo",system-ui,sans-serif;padding:28px 48px}
h1{font-size:32px;margin:0 0 14px}form{display:flex;gap:10px;margin-bottom:14px}
select{font:inherit;background:#1c1f28;color:#e8eaf0;border:1px solid #39404f;border-radius:10px;padding:8px 12px;max-width:900px}
button{font:inherit;background:#4f7cf0;color:#fff;border:0;border-radius:10px;padding:8px 18px}
.sum{display:flex;gap:28px;margin:6px 0 16px;color:#9aa1b2}.sum b{color:#e8eaf0}
.cols{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.col h2{font-size:21px;margin:0 0 8px}
.it{background:#1a1d26;border:1px solid #2c313c;border-radius:8px;padding:6px 10px;margin-bottom:6px;font-size:15px;color:#9aa1b2}
.it.ok{border-color:#4fb37a;background:#16261d;color:#d6f5e0}.r{color:#e0a43a;font-weight:700;margin-right:6px}"""


def page(qi=0, label="원래 질문"):
    data = json.loads((DIR / "compare.json").read_text())[label]
    q = QS[qi]
    opts = "".join(
        f'<option value="{i}"{" selected" if i == qi else ""}>{html.escape(x["q"][:60])}</option>'
        for i, x in enumerate(QS)
    )
    labs = "".join(
        f"<option{' selected' if lab == label else ''}>{lab}</option>"
        for lab in ("원래 질문", "말 바꾼 질문")
    )
    out = f"""<!doctype html><meta charset="utf-8"><title>순위 디버그</title><style>{CSS}</style>
<h1>순위 디버그 · 검색 4종</h1><form><select name="i">{opts}</select><select name="l">{labs}</select><button>보기</button></form>
<p>질문: <b>{html.escape(q["q"] if label == "원래 질문" else q["q_para"])}</b> · 회사 필터 {html.escape(q["corp"])}</p><div class="sum">"""
    for m, name in NAMES.items():
        out += f"<span>{name} recall@5 <b>{data[m]['recall@5']:.3f}</b></span>"
    out += '</div><div class="cols">'
    for m, name in NAMES.items():
        out += f'<div class="col"><h2>{name}</h2>'
        for r, i in enumerate(data[m]["ranked"][qi][:10]):
            c = CHUNKS[i]
            ok = is_gold(c, q)
            out += f'<div class="it{" ok" if ok else ""}"><span class="r">{r + 1}</span>{"✅ " if ok else ""}{html.escape(c["section"][-38:])}</div>'
        out += "</div>"
    return out + "</div>"


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        p = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        b = page(int(p.get("i", ["0"])[0]), p.get("l", ["원래 질문"])[0]).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("http://127.0.0.1:8808")
    HTTPServer(("127.0.0.1", 8808), H).serve_forever()
