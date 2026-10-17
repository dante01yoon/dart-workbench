"""원격 MCP 인증 시험 (강의 17편): 잘못된 토큰 5종은 모두 거절되고, 맞는 토큰만 통과해야 한다. 토큰 값은 출력하지 않는다.
사용: .venv/bin/python mcp_server/auth_test.py"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dart_rag import dart  # noqa: E402,F401  (.env)

URL = os.environ.get("MCP_TEST_URL", "http://127.0.0.1:8790/mcp")  # 원격: https://dart-mcp-324k.onrender.com/mcp
META = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientInfo": {"name": "auth-test", "version": "0"}, "io.modelcontextprotocol/clientCapabilities": {}}


def call(auth, method="tools/call", params=None):
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": {"_meta": META, **(params or {})}}
    # 2026-07-28 HTTP: 본문의 method·name을 헤더에도 적어야 한다(Mcp-Method, Mcp-Name). 빠지면 400(-32020).
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2026-07-28",
         "Mcp-Method": method}
    if (params or {}).get("name"):
        h["Mcp-Name"] = params["name"]
    if auth is not None:
        h["Authorization"] = auth
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=h)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode()[:300], time.time() - t0, r.headers.get("WWW-Authenticate")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200], time.time() - t0, e.headers.get("WWW-Authenticate")


E = os.environ
FIN = {"name": "get_financials", "arguments": {"corp": "삼성전자", "year": 2025}}
cases = [
    ("토큰 없음", None, 401),
    ("틀린 토큰", "Bearer " + "x" * 43, 401),
    ("Bearer 없이 토큰만", E["MCP_TOKEN_GOOD"], 401),
    ("스코프 부족(profile)", "Bearer " + E["MCP_TOKEN_NOSCOPE"], 403),
    ("다른 서버용 토큰(resource 불일치)", "Bearer " + E["MCP_TOKEN_OTHER"], 401),
    ("올바른 토큰", "Bearer " + E.get("MCP_TEST_TOKEN", E["MCP_TOKEN_GOOD"]), 200),
]
ok = 0
for name, auth, want in cases:
    code, body, sec, www = call(auth, params=FIN)
    passed = code == want or (want == 401 and code in (401, 403))
    ok += passed
    print(f"{'✅' if passed else '❌'} {name:28s} → HTTP {code} ({sec * 1000:.0f}ms)" + (f"  WWW-Authenticate: {www[:90]}" if www else ""))
print(f"{ok}/{len(cases)} 기대대로")

lat = []
GOOD = "Bearer " + E.get("MCP_TEST_TOKEN", E["MCP_TOKEN_GOOD"])
for _ in range(5):
    lat.append(call(GOOD, params=FIN)[2])
print(f"{URL} get_financials 지연: 중앙값 {sorted(lat)[2] * 1000:.0f}ms")
print("응답 앞부분:", call(GOOD, params=FIN)[1][:120])
