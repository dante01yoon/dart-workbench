"""23~25편 공통: 결과를 로컬 웹 화면 하나로 띄운다(127.0.0.1 전용, 외부 공개 없음)."""

import http.server
import socketserver

CSS = """
body{margin:0;background:#14161c;color:#e8e6e1;font:22px/1.5 'Noto Sans KR',system-ui,sans-serif}
main{max-width:1760px;margin:0 auto;padding:36px 48px}
h1{font-size:40px;margin:0 0 6px}h2{font-size:30px;margin:34px 0 12px;color:#f2b84b}
.sub{color:#9aa0aa;margin:0 0 22px}
table{border-collapse:collapse;width:100%;font-size:21px}
th,td{border-bottom:1px solid #2c303a;padding:10px 12px;text-align:left;vertical-align:top}
th{color:#9aa0aa;font-weight:600}
.ok{color:#7fd18b}.part{color:#f2b84b}.no{color:#ef7a6b}
.num{font-family:'JetBrains Mono',monospace;white-space:nowrap}
.grid{display:grid;gap:16px}
.card{background:#1d2028;border:1px solid #2c303a;border-radius:14px;padding:18px 20px}
.card b{font-size:24px}.tag{display:inline-block;padding:2px 10px;border-radius:99px;background:#2c303a;font-size:18px;margin:2px 4px 2px 0}
.dot{display:inline-block;width:26px;height:26px;border-radius:6px;background:#2c303a}
.dot.on{background:#f2b84b}
"""


def page(title, body):
    return f"<!doctype html><meta charset=utf-8><title>{title}</title><style>{CSS}</style><main>{body}</main>"


def serve(html, port):
    data = html.encode()

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), H) as s:
        print(f"화면 → http://127.0.0.1:{port}  (끝내려면 Ctrl+C)", flush=True)
        try:
            s.serve_forever()
        except KeyboardInterrupt:
            print("\n화면을 닫았어요.")
