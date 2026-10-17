"""17편 01: 원격 MCP 인증 시험 — 틀린 토큰은 모두 거절되고, 맞는 토큰만 통과해야 한다. 토큰 값은 출력하지 않는다.

uv run python sec17/01_auth_test.py                                   # 내 컴퓨터(127.0.0.1:8790)
uv run python sec17/01_auth_test.py https://dart-mcp-324k.onrender.com/mcp   # 배포한 서버
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec02"))
import tools15  # noqa: F401  (.env를 읽는다)

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8790/mcp"
REMOTE = not URL.startswith("http://127.0.0.1")
META = {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientInfo": {"name": "auth-test-17", "version": "0.1"},
    "io.modelcontextprotocol/clientCapabilities": {},
}
FIN = {"name": "get_financials", "arguments": {"corp": "삼성전자"}}
if REMOTE:  # 배포판은 2024 · 2025 두 해를 담은 참조 서버라 year 인자가 있다
    FIN["arguments"]["year"] = 2025


def call(auth, params=FIN, method="tools/call", headers=True):
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": {"_meta": META, **params}}
    h = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2026-07-28",
    }
    if headers:  # 2026-07-28 HTTP: 본문의 method · 도구 이름을 헤더에도 적는다
        h["Mcp-Method"] = method
        if params.get("name"):
            h["Mcp-Name"] = params["name"]
    if auth is not None:
        h["Authorization"] = auth
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=h)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read().decode(), time.time() - t0, None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), time.time() - t0, e.headers.get("WWW-Authenticate")


E = os.environ
good = "Bearer " + (E["MCP_TOKEN_REMOTE"] if REMOTE else E["MCP_TOKEN_GOOD"])
cases = [
    ("토큰 없음", None, 401),
    ("틀린 토큰", "Bearer " + "x" * 43, 401),
    ("Bearer 없이 토큰만", good.split()[1], 401),
]
if not REMOTE:
    cases += [
        ("스코프 부족(profile만)", "Bearer " + E["MCP_TOKEN_NOSCOPE"], 403),
        ("다른 서버용 토큰", "Bearer " + E["MCP_TOKEN_OTHER"], 401),
    ]
cases += [("올바른 토큰", good, 200)]

print(f"■ {URL}\n")
if REMOTE:  # 무료 인스턴스는 쉬면 잠든다 → 첫 요청으로 깨운다
    code, _, sec, _ = call(good)
    print(f"  깨우기: HTTP {code} ({sec:.1f}초)\n")
ok = 0
for name, auth, want in cases:
    code, body, sec, www = call(auth)
    passed = code == want
    ok += passed
    tail = f"  {www.split(',')[0][:40]}" if www else ""
    print(f"  {'○' if passed else '×'} {name:<16} → HTTP {code} ({sec * 1000:.0f}ms){tail}")
print(f"\n  {ok}/{len(cases)} 기대대로")

# 401 응답의 WWW-Authenticate가 가리키는 '보호 리소스 메타데이터': 어떤 인가 서버 · 스코프가 필요한지 알려 준다
www = call(None)[3]
meta_url = www.split('resource_metadata="')[1].split('"')[0]
meta = json.loads(urllib.request.urlopen(meta_url, timeout=60).read())
print(f"\n■ 401이 알려 준 메타데이터 주소: {meta_url}")
print(f"  resource={meta['resource']}  scopes={meta['scopes_supported']}")

code, body, _, _ = call(good, headers=False)
print(f"\n■ Mcp-Method 헤더를 빼면 → HTTP {code} {body[:90]}")

LIST = {"name": "list_reports", "arguments": {}}  # 파일만 읽는 도구 → 순수 왕복 시간
lat = sorted(call(good, LIST)[2] for _ in range(5))
code, body, _, _ = call(good)
text = body.split("data: ", 1)[-1] if "data: " in body else body
res = json.loads(text)["result"]["content"][0]["text"]
print(f"\n■ list_reports 5번 왕복: 중앙값 {lat[2] * 1000:.0f}ms")
print("■ get_financials 결과 앞부분:")
print("  ", res.replace("\n", " ")[:110], "…")
