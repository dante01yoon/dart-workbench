"""26편 ② 메모 달기 — 기록(트레이스)을 한 문항씩 읽고, 무엇이 잘못됐는지 한 줄 메모와 "처음 틀어진 단계"를 적는다.

- 채점기가 틀렸다고 한 문항이 먼저, 맞았다고 한 문항이 뒤에 온다(맞았다는 판정도 틀릴 수 있다).
- 처음 틀어진 단계: 에이전트 안(계획 · 공시 검색 · 재무 조회 · 뉴스 검색 · 작성 · 심판) 또는 에이전트 밖(채점기 · 정답 키).
- 메모는 사람이 쓴다. 이 단계에서 유형 이름을 미리 정하지 않는다(열린 메모).
사용: uv run python sec26/02_memo.py → http://127.0.0.1:8829 (저장하면 data/memos26.json)
"""

import html
import http.server
import json
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sec23"))
from page import page

TRACES = [json.loads(line) for line in (ROOT / "data" / "traces26.jsonl").open()]
MEMOS = ROOT / "data" / "memos26.json"
STAGES = ["계획", "공시 검색", "재무 조회", "뉴스 검색", "작성", "심판", "채점기", "정답 키"]
WORKER = {"filings": "공시 검색", "financials": "재무 조회", "news": "뉴스 검색"}

CSS = """<style>
.item{background:#1d2028;border:1px solid #2c303a;border-radius:14px;padding:20px 24px;margin:0 0 28px}
.q{font-size:28px;font-weight:700}.key{color:#9aa0aa;font-size:20px}
.flow{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.st{padding:6px 12px;border-radius:10px;background:#2c303a;font-size:19px}
.st.zero{background:#5a2a26}.sent{font-size:20px;margin:4px 0}.b{font-size:16px;padding:1px 8px;border-radius:99px;background:#2c303a;margin-left:6px}
textarea{width:100%;height:64px;font:22px 'Noto Sans KR',sans-serif;background:#14161c;color:#e8e6e1;border:1px solid #f2b84b;border-radius:8px;padding:8px}
.pick{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}.pick label{padding:6px 12px;border-radius:10px;background:#2c303a;font-size:19px;cursor:pointer}
.pick input{display:none}.pick input:checked+span{color:#14161c}.pick label:has(input:checked){background:#f2b84b;color:#14161c}
#save{position:fixed;right:30px;bottom:24px;font-size:24px;padding:12px 26px;border-radius:12px;background:#f2b84b;border:0}
</style>"""


def flow(x):
    """한 줄 궤적: 계획 → 작업마다(담당 · 찾은 근거 수 · 끝난 시각) → 작성 → 심판"""
    ev = x["events"]
    if x["refused"]:
        return "<span class=st>계획에서 거절</span>"
    plan = next((e for e in ev if e["type"] == "plan"), {"tasks": []})
    out = [f"<span class=st>계획: 작업 {len(plan['tasks'])}개</span>"]
    q = {t["id"]: t for t in plan["tasks"]}
    for e in [e for e in ev if e["type"] == "task_end"]:
        t = q[e["id"]]
        out.append(
            f"<span class='st{' zero' if not e['n'] else ''}'>{WORKER[t['worker']]} · {html.escape(t['query'][:26])} → 근거 {e['n']} · {e['t']:.0f}초</span>"
        )
    w = next((e for e in ev if e["type"] == "writing"), None)
    if w:
        out.append(f"<span class=st>작성: 확인된 근거 {w['evidence']}개</span>")
    for v in [e for e in ev if e["type"] == "verify"]:
        out.append(f"<span class=st>심판 {v['round']}회: 지지 {v['ok']}/{v['total']}</span>")
    return " ".join(out)


def item(x, memo):
    key = "거절해야 정답" if x["keys"] == "refuse" else " · ".join("/".join(g) for g in x["keys"])
    sents = (
        "".join(
            f"<div class=sent>{html.escape(s['sentence'])}<span class=b>{s['badge']}</span></div>"
            for s in x["report"]
        )
        or "<div class=sent>(보고서 없음)</div>"
    )
    pick = "".join(
        f"<label id='s-{x['id']}-{s.replace(' ', '')}'><input type=radio name='s-{x['id']}' value='{s}'"
        f"{' checked' if memo.get('stage') == s else ''}><span>{s}</span></label>"
        for s in STAGES
    )
    return (
        f"<div class=item id='it-{x['id']}'><div class=q>{x['id']} {'✅' if x['correct'] else '❌'} {html.escape(x['q'])}</div>"
        f"<div class=key>정답 키: {html.escape(key)} · {x['seconds']:.0f}초 · ${x['cost']:.4f}</div>"
        f"<div class=flow>{flow(x)}</div>{sents}"
        f"<textarea spellcheck=false id='m-{x['id']}' placeholder='무엇이 잘못됐나 — 한 줄'>{html.escape(memo.get('memo', ''))}</textarea>"
        f"<div class=pick>처음 틀어진 단계: {pick}</div></div>"
    )


def render():
    memos = json.loads(MEMOS.read_text()) if MEMOS.exists() else {}
    order = sorted(TRACES, key=lambda x: x["correct"])  # 틀린 것 먼저
    bad = sum(not x["correct"] for x in TRACES)
    js = (
        "<script>document.getElementById('save').onclick=async()=>{const d={};"
        "document.querySelectorAll('.item').forEach(it=>{const id=it.id.slice(3);"
        "const m=document.getElementById('m-'+id).value.trim();const s=it.querySelector('input:checked');"
        "if(m||s)d[id]={memo:m,stage:s?s.value:''};});"
        "const r=await fetch('/save',{method:'POST',body:JSON.stringify(d)});"
        "document.getElementById('save').textContent='저장됨 · '+(await r.text());};</script>"
    )
    body = (
        f"<h1>메모 달기 · {len(TRACES)}문항</h1><p class=sub>채점기 판정: 틀림 {bad} · 맞음 {len(TRACES) - bad} — 틀린 것부터, "
        "기록을 읽고 무엇이 잘못됐는지 한 줄씩</p>"
        + "".join(item(x, memos.get(x["id"], {})) for x in order)
        + "<button id=save>저장</button>"
        + js
    )
    return page("메모 달기", CSS + body)


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.reply(render())

    def do_POST(self):
        d = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        MEMOS.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        print(f"메모 {len(d)}개 저장 → data/memos26.json", flush=True)
        self.reply(f"메모 {len(d)}개")

    def reply(self, text):
        data = text.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", 8829), H) as s:
        print("메모 화면 → http://127.0.0.1:8829  (끝내려면 Ctrl+C)", flush=True)
        try:
            s.serve_forever()
        except KeyboardInterrupt:
            print("\n화면을 닫았어요.")
