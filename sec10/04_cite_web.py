"""10편 ④ 원문 하이라이트 화면 — data/rag/cite_eval.json을 읽어 문항마다 답 문장 · 인용 확인 결과와,
인용한 발췌 원문을 나란히 보여 준다. 문장에 나온 숫자는 원문에서 노란색으로 칠한다. 맨 위는 문항 종류별 성적표.
사용: uv run python sec10/04_cite_web.py → http://127.0.0.1:8810"""

import html
import json
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from cite import DIR, NUM, load_store, sentences

CHUNKS = {c["id"]: c for c in load_store()[0]}
TYPES = {"number": "숫자", "narrative": "서술", "none": "근거 없음", "refuse": "투자 권유"}
CSS = """body{margin:0;background:#111317;color:#e8eaf0;font:18px/1.55 "Apple SD Gothic Neo",system-ui,sans-serif;padding:24px 40px}
h1{font-size:30px;margin:0 0 12px}form{display:flex;gap:10px;margin:12px 0}
select{font:inherit;background:#1c1f28;color:#e8eaf0;border:1px solid #39404f;border-radius:10px;padding:6px 12px;max-width:900px}
button{font:inherit;background:#4f7cf0;color:#fff;border:0;border-radius:10px;padding:6px 16px}
table{border-collapse:collapse;font-size:17px}td,th{border:1px solid #2c313c;padding:5px 14px;text-align:center}th{background:#1a1d26}
.wrap{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:10px}.box{background:#1a1d26;border:1px solid #2c313c;border-radius:14px;padding:14px 18px}
.s{margin:8px 0;padding:6px 10px;border-left:4px solid #4fb37a}.s.bad{border-color:#e05d5d}.s.na{border-color:#6b7280}
.tag{font-size:14px;border-radius:6px;padding:1px 8px;margin-left:6px;background:#23402f;color:#9fe0b5}.bad .tag{background:#4a2323;color:#f3a9a9}
.src{font-size:15px;color:#b8bfcc;white-space:pre-wrap;max-height:300px;overflow:hidden;margin:8px 0 14px}.src b{color:#e8eaf0}
mark{background:#f2c14e;color:#111;border-radius:3px;padding:0 2px}"""


def scorecard(rows):
    out = "<table><tr><th>종류</th><th>문항</th><th>정답</th><th>인용 확인(문장)</th></tr>"
    for t, name in TYPES.items():
        rs = [r for r in rows if r["type"] == t]
        sents = [c for r in rs for c in r["checks"]]
        ok = sum(c in ("확인", "계산") for c in sents)
        out += f"<tr><td>{name}</td><td>{len(rs)}</td><td>{sum(r['correct'] for r in rs)}</td><td>{f'{ok}/{len(sents)}' if sents else '-'}</td></tr>"
    return out + "</table>"


def page(i=0):
    rows = json.loads((DIR / "cite_eval.json").read_text())
    r = rows[i]
    opts = "".join(
        f'<option value="{n}"{" selected" if n == i else ""}>{x["id"]} · {html.escape(x["q"])}</option>'
        for n, x in enumerate(rows)
    )
    sents = sentences(r["answer"])
    left = ""
    nums = set()
    for n, s in enumerate(sents):
        c = r["checks"][n] if n < len(r["checks"]) else r["kind"]
        cls = "" if c in ("확인", "계산", "근거 없음", "투자 거절") else " bad"
        left += f'<div class="s{cls}">{html.escape(s)}<span class="tag">{html.escape(c)}</span></div>'
        nums |= {x for x in NUM.findall(re.sub(r"\[\d+\]", "", s)) if len(x.replace(",", "")) >= 3}
    if r["api"]:
        a = r["api"]
        left += (
            f"<p>재무 API {a['account']} {a['value']:,}원 → <b>{'일치' if a['match'] else '불일치'}</b></p>"
        )
    cited = sorted({int(x) for x in re.findall(r"\[(\d+)\]", r["answer"])})
    right = ""
    for n in cited:
        if n > len(r["hits"]):
            continue
        ch = CHUNKS[r["hits"][n - 1]]
        body = html.escape(ch["text"][:900])
        for x in sorted(nums, key=len, reverse=True):
            body = body.replace(html.escape(x), f"<mark>{html.escape(x)}</mark>")
        right += f'<div><b>[{n}] {html.escape(ch["corp"] + " · " + ch["section"][-40:])}</b><div class="src">{body}</div></div>'
    return f"""<!doctype html><meta charset="utf-8"><title>출처 확인</title><style>{CSS}</style>
<h1>출처 확인 · 원문 하이라이트</h1>{scorecard(rows)}
<form><select name="i">{opts}</select><button>보기</button></form>
<div class="wrap"><div class="box"><b>답</b>{left}</div><div class="box"><b>인용한 원문</b>{right or "<p>인용 없음</p>"}</div></div>"""


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
    print("http://127.0.0.1:8810")
    HTTPServer(("127.0.0.1", 8810), H).serve_forever()
