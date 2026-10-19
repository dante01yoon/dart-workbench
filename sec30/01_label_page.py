"""30편 ① 라벨링 페이지 — 질문 · 답 · 근거(요약 + 원문 인용)를 한 화면에 띄우고 통과/실패/보류 + 이유를 JSON 한 줄로 저장한다.

판단에 필요한 것은 한 화면에(답 문장마다 붙은 근거 id, 근거의 원문 인용). 판사 판정은 보여 주지 않는다 — 먼저 보면 따라가게 된다.
대기열 기본값: 29편 R6 원본 답 8개(판사가 그중 3개에 '아니오' — 사람 R6 라벨이 아직 없다).
저장: data/labels30_new.jsonl (한 줄 = 라벨 하나, 걸린 시간 포함). 단축키 1 통과 · 2 실패 · 3 보류 · Enter 저장.
사용: uv run python sec30/01_label_page.py [--labeler 이름] → http://127.0.0.1:8840
"""

import html
import http.server
import json
import socketserver
import sys
from datetime import datetime

from labels import DATA, GUIDE, TRACES

QUEUE = [r["id"] for r in json.loads((DATA / "judge29.json").read_text())["b"] if not r["fake"]]
OUT = DATA / "labels30_new.jsonl"
LABELER = sys.argv[sys.argv.index("--labeler") + 1] if "--labeler" in sys.argv else "나"
CRIT = "R6"


def item(qid):
    x = TRACES[qid]
    sents = "".join(
        f"<li>{html.escape(s['sentence'])} <span class=cite>{' · '.join(s['cites']) or '인용 없음'}</span></li>"
        for s in x["report"]
    )
    ev = "".join(
        f"<div class=ev><b>{e['id']}</b> <span class=src>{html.escape(e['source'])}</span><div>요약: {html.escape(e['claim'])}</div>"
        f"<div class=quote>원문: {html.escape(e.get('quote', ''))}</div></div>"
        for e in x["evidence"]
    )  # fmt: skip
    return f"<section data-id={qid}><h2>{qid} · {html.escape(x['q'])}</h2><div class=cols><div><h3>답</h3><ol>{sents}</ol></div><div><h3>근거</h3>{ev}</div></div></section>"


CSS = """body{margin:0;background:#14161c;color:#e8e6e1;font:20px/1.5 'Noto Sans KR',system-ui,sans-serif}
header{display:flex;gap:24px;align-items:center;padding:14px 32px;background:#1d2028;border-bottom:1px solid #2c303a}
header b{font-size:26px}.pill{padding:2px 12px;border-radius:99px;background:#2c303a;font-size:18px}
main{display:grid;grid-template-columns:1fr 470px;gap:24px;padding:18px 32px}
h2{margin:0 0 8px;font-size:28px;color:#f2b84b}h3{margin:6px 0;color:#9aa0aa;font-size:19px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:20px}ol{margin:0;padding-left:26px}li{margin:6px 0}
.cite{font-size:15px;color:#7fb4ef}.ev{background:#1d2028;border:1px solid #2c303a;border-radius:10px;padding:8px 12px;margin:0 0 8px;font-size:17px}
.src{color:#9aa0aa;font-size:14px}.quote{color:#cfd6a4}aside{background:#1d2028;border:1px solid #2c303a;border-radius:14px;padding:16px}
.guide{font-size:17px;color:#c9c6bf}.btns{display:flex;gap:8px;margin:12px 0}
button{font:inherit;font-size:22px;padding:8px 16px;border-radius:10px;border:2px solid #2c303a;background:#262a33;color:#e8e6e1;cursor:pointer}
button.on{border-color:#f2b84b;background:#3a3220}textarea,select{width:100%;font:inherit;font-size:18px;background:#14161c;color:#e8e6e1;border:1px solid #2c303a;border-radius:8px;padding:8px;box-sizing:border-box}
#saved{font:15px/1.4 'JetBrains Mono',monospace;color:#7fd18b;white-space:pre-wrap;word-break:break-all;margin-top:10px}"""

JS = """let i=0,label=null,t0=Date.now();const items=[...document.querySelectorAll('section')];
function show(){items.forEach((s,k)=>s.style.display=k==i?'':'none');document.getElementById('prog').textContent=(i+1)+' / '+items.length;
label=null;document.querySelectorAll('.btns button').forEach(b=>b.classList.remove('on'));document.getElementById('why').value='';t0=Date.now();}
function pick(v){label=v;document.querySelectorAll('.btns button').forEach(b=>b.classList.toggle('on',b.dataset.v==v));document.getElementById('stagebox').style.display=v=='실패'?'':'none';}
async function save(){if(!label)return;const r={id:items[i].dataset.id,criterion:CRIT,label,reason:document.getElementById('why').value,
stage:label=='실패'?document.getElementById('stage').value:'',labeler:LABELER,guide:GUIDE,seconds:Math.round((Date.now()-t0)/1000)};
const res=await fetch('/label',{method:'POST',body:JSON.stringify(r)});document.getElementById('saved').textContent='저장 → data/labels30_new.jsonl\\n'+await res.text();
if(i<items.length-1){i++;show();}}
document.addEventListener('keydown',e=>{if(e.target.tagName=='TEXTAREA'&&e.key!='Enter')return;if(e.key=='1')pick('통과');if(e.key=='2')pick('실패');if(e.key=='3')pick('보류');if(e.key=='Enter'){e.preventDefault();save();}});
show();"""


def page():
    stages = "".join(
        f"<option>{s}</option>" for s in ("작성", "공시 검색", "재무 조회", "뉴스 검색", "계획", "채점기")
    )
    return f"""<!doctype html><meta charset=utf-8><title>라벨링</title><style>{CSS}</style>
<header><b>라벨링 · 기준 {CRIT} 지어내지 않음</b><span class=pill id=prog></span><span class=pill>라벨러 {html.escape(LABELER)}</span><span class=pill>지침 {GUIDE["version"]}</span></header>
<main><div>{"".join(item(q) for q in QUEUE)}</div>
<aside><h3>지침</h3><div class=guide>{GUIDE[CRIT]}<br>{GUIDE["보류"]}</div>
<div class=btns><button data-v=통과 onclick="pick('통과')">1 통과</button><button data-v=실패 onclick="pick('실패')">2 실패</button><button data-v=보류 onclick="pick('보류')">3 보류</button></div>
<h3>이유 (자유 글)</h3><textarea id=why rows=3></textarea>
<div id=stagebox style=display:none><h3>처음 틀어진 단계</h3><select id=stage>{stages}</select></div>
<div class=btns><button id=savebtn onclick=save()>저장 (Enter)</button></div><div id=saved></div></aside></main>
<script>const CRIT={json.dumps(CRIT)},LABELER={json.dumps(LABELER, ensure_ascii=False)},GUIDE={json.dumps(GUIDE["version"], ensure_ascii=False)};{JS}</script>"""


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.reply(page())

    def do_POST(self):
        r = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if (
            r.get("label") not in ("통과", "실패", "보류") or r.get("id") not in TRACES
        ):  # 화면 밖에서 온 이상한 줄은 받지 않는다
            return self.reply("거절", 400)
        r["at"] = datetime.now().isoformat(timespec="seconds")
        line = json.dumps(r, ensure_ascii=False)
        with OUT.open("a") as f:
            f.write(line + "\n")
        print("저장", line, flush=True)
        self.reply(line)

    def reply(self, text, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(text.encode())

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(
        f"라벨링 대기열 {len(QUEUE)}문항 · 기준 {CRIT} · 라벨러 {LABELER} · 저장 {OUT.relative_to(DATA.parent)}"
    )
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", 8840), H) as s:
        print("화면 → http://127.0.0.1:8840  (끝내려면 Ctrl+C)", flush=True)
        try:
            s.serve_forever()
        except KeyboardInterrupt:
            print("\n화면을 닫았어요.")
