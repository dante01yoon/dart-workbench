"""7편 ⑤ 출처 링크 Q&A 화면 — 질문을 넣으면 RAG로 답하고, 근거 조각마다 섹션 경로와 DART 원문 링크를 단다.
사용: uv run python sec07/05_qa_web.py  → http://127.0.0.1:8807"""

import html
import importlib.util
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from rag import CORPS, YEAR, load_store

spec = importlib.util.spec_from_file_location("rag04", Path(__file__).with_name("04_rag.py"))
rag04 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rag04)
CHUNKS, EMB = load_store()
CSS = """body{margin:0;background:#111317;color:#e8eaf0;font:20px/1.6 "Apple SD Gothic Neo",system-ui,sans-serif;padding:36px 64px}
h1{font-size:34px;margin:0 0 18px}form{display:flex;gap:12px;margin-bottom:26px}
select,input{font:inherit;background:#1c1f28;color:#e8eaf0;border:1px solid #39404f;border-radius:10px;padding:10px 14px}
input{flex:1}button{font:inherit;background:#4f7cf0;color:#fff;border:0;border-radius:10px;padding:10px 22px}
.ans{background:#1a1d26;border:1px solid #2c313c;border-radius:14px;padding:20px 24px;white-space:pre-wrap}
.src{margin-top:14px;border-left:4px solid #e0a43a;padding:8px 16px;background:#16181f;border-radius:6px}
.src a{color:#8fb0ff}.src pre{white-space:pre-wrap;color:#9aa1b2;font-size:16px;margin:6px 0 0}.n{color:#e0a43a;font-weight:700}
.meta{color:#9aa1b2;font-size:16px;margin:10px 0}"""


def page(q="", corp=CORPS[0]):
    opts = "".join(f"<option{' selected' if c == corp else ''}>{c}</option>" for c in CORPS)
    out = f"""<!doctype html><meta charset="utf-8"><title>출처 링크 Q&A</title><style>{CSS}</style>
<h1>출처 링크 Q&A · {YEAR} 사업보고서</h1>
<form action="/"><select name="corp">{opts}</select><input name="q" value="{html.escape(q)}" placeholder="질문"><button>묻기</button></form>"""
    if q:
        text, hits, tok, cost = rag04.answer(q, corp, CHUNKS, EMB)
        body = re.sub(r"\[(\d)\]", r'<span class="n">[\1]</span>', html.escape(text))
        out += f'<div class="ans">{body}</div><p class="meta">입력 {tok:,}토큰 · ${cost:.4f} · 근거 조각 {len(hits)}개</p>'
        for n, i in enumerate(hits):
            c = CHUNKS[i]
            url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={c['rcept_no']}"
            out += (
                f'<div class="src"><span class="n">[{n + 1}]</span> {html.escape(c["corp"])} {c["year"]} · '
                f'{html.escape(c["section"])} · <a href="{url}">DART 원문</a><pre>{html.escape(c["text"][:220])}…</pre></div>'
            )
    return out


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        b = page(qs.get("q", [""])[0], qs.get("corp", [CORPS[0]])[0]).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("http://127.0.0.1:8807")
    HTTPServer(("127.0.0.1", 8807), H).serve_forever()
