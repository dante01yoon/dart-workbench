"""과제 2 풀이: 예전 클라이언트(2025-11-25)처럼 initialize 핸드셰이크로 붙어 본다.
우리 서버는 두 시대를 다 받는다(dual-era): initialize가 오면 그 연결은 예전 방식으로, _meta 없이도 답한다.
사용: uv run python sec15/solutions/a2_legacy_client.py
"""

import json
import subprocess
import sys
from pathlib import Path

SERVER = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "server.py"
p = subprocess.Popen(
    [sys.executable, str(SERVER)],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
)


def send(msg, expect=True):
    p.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
    p.stdin.flush()
    if expect:
        r = json.loads(p.stdout.readline())
        print("→", msg["method"])
        print("←", json.dumps(r, ensure_ascii=False)[:160])
        return r


send(
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "old-client", "version": "1"},
        },
    }
)
send({"jsonrpc": "2.0", "method": "notifications/initialized"}, expect=False)  # 알림: 답이 없다
r = send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})  # _meta 없이
print("도구:", [t["name"] for t in r["result"]["tools"]])
r = send(
    {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "get_financials", "arguments": {"corp": "카카오"}},
    }
)
print(json.loads(r["result"]["content"][0]["text"])["accounts"])
p.stdin.close()
p.wait()
