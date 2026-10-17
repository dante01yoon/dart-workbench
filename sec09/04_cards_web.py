"""9편 ④ 비교 카드 화면 — data/rag/cross.json을 읽어, 비교 질문마다 회사별 카드를 보여 준다(표준 라이브러리만).
카드 = LLM이 쓴 그 회사의 하위 질문 + 합친 상위 10개 중 그 회사 조각과 순위(정답 조각 ✅). 맨 위에는 한 번에 찾았을 때 확보한 회사.
사용: uv run python sec09/04_cards_web.py → http://127.0.0.1:8809"""

import html
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from context import DIR
from search import load_store
from tools15 import ROOT

CHUNKS, _ = load_store()
QS = {
    json.loads(line)["id"]: json.loads(line)
    for line in (ROOT / "eval" / "questions.jsonl").open(encoding="utf-8")
}
CSS = """body{margin:0;background:#111317;color:#e8eaf0;font:19px/1.5 "Apple SD Gothic Neo",system-ui,sans-serif;padding:28px 48px}
h1{font-size:32px;margin:0 0 14px}form{display:flex;gap:10px;margin-bottom:14px}
select{font:inherit;background:#1c1f28;color:#e8eaf0;border:1px solid #39404f;border-radius:10px;padding:8px 12px}
button{font:inherit;background:#4f7cf0;color:#fff;border:0;border-radius:10px;padding:8px 18px}
.once{color:#9aa1b2;margin:4px 0 18px}.once b{color:#e8eaf0}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:16px}
.card{background:#1a1d26;border:1px solid #2c313c;border-radius:14px;padding:16px 18px}.card h2{font-size:24px;margin:0 0 6px}
.sub{color:#e0a43a;font-size:17px;margin-bottom:10px}.it{font-size:15px;color:#9aa1b2;border-left:3px solid #2c313c;padding:4px 10px;margin:6px 0}
.it.ok{border-color:#4fb37a;color:#d6f5e0}"""


def gold(c, g):
    return (not g.get("section") or g["section"] in c["section"]) and any(
        s in c["text"] for s in g["contains"]
    )


def page(n=0):
    d = json.loads((DIR / "cross.json").read_text())
    q = QS[d["questions"][n]]
    opts = "".join(
        f'<option value="{i}"{" selected" if i == n else ""}>{html.escape(QS[x]["q"])}</option>'
        for i, x in enumerate(d["questions"])
    )
    once = [
        c
        for c, g in q["gold_multi"].items()
        if any(CHUNKS[i]["corp"] == c and gold(CHUNKS[i], g) for i in d["runs"]["한 번에"][n])
    ]
    out = f"""<!doctype html><meta charset="utf-8"><title>비교 카드</title><style>{CSS}</style>
<h1>비교 카드 · 나눠 찾기</h1><form><select name="n">{opts}</select><button>보기</button></form>
<p class="once">한 번에 찾았을 때 상위 10개에서 근거를 찾은 회사: <b>{html.escape(", ".join(once) or "없음")}</b> / {len(q["gold_multi"])}곳</p><div class="cards">"""
    subs = {s["corp"]: s["q"] for s in d["subs"][n]}
    for corp, g in q["gold_multi"].items():
        ranked = d["runs"]["LLM 분해"][n]
        mine = [
            (r, i) for r, i in enumerate(ranked, 1) if CHUNKS[i]["corp"] == corp
        ]  # 합친 상위 10개 중 이 회사 조각 전부
        out += f'<div class="card"><h2>{html.escape(corp)}</h2><div class="sub">하위 질문: {html.escape(subs.get(corp, "-"))}</div>'
        for r, i in mine:
            ok = gold(CHUNKS[i], g)
            out += f'<div class="it{" ok" if ok else ""}">{r}위 {"✅ " if ok else ""}{html.escape(CHUNKS[i]["section"][-40:])}</div>'
        out += "</div>"
    return out + "</div>"


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        p = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        b = page(int(p.get("n", ["0"])[0])).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("http://127.0.0.1:8809")
    HTTPServer(("127.0.0.1", 8809), H).serve_forever()
