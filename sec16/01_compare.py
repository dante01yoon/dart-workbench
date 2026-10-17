"""16편 01: 손으로 만든 서버(15편) vs SDK 서버 — 코드 줄 수와, 같은 요청에 대한 답을 나란히 본다.

1. 코드 줄 수(빈 줄 · 주석 · docstring 제외)
2. 15편 클라이언트처럼 _meta에 버전만 실은 요청 → 두 서버의 반응
3. 정식 _meta로 discover → 두 서버가 알려 주는 것(버전 · 기능 · 캐시)
"""

import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVERS = {"손 구현(15편)": ROOT / "sec15" / "server.py", "SDK(16편)": ROOT / "sec16" / "server_sdk.py"}
VERSION = {"io.modelcontextprotocol/protocolVersion": "2026-07-28"}
FULL = {
    **VERSION,
    "io.modelcontextprotocol/clientInfo": {"name": "cmp-16", "version": "0.1"},
    "io.modelcontextprotocol/clientCapabilities": {},
}


def code_lines(path):
    src = path.read_text()
    doc = set()
    for node in ast.walk(ast.parse(src)):  # docstring 줄은 세지 않는다
        body = getattr(node, "body", None)
        if (
            isinstance(body, list)
            and body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
        ):
            doc.update(range(body[0].lineno, body[0].end_lineno + 1))
    return sum(
        1
        for n, line in enumerate(src.splitlines(), 1)
        if line.strip() and not line.strip().startswith("#") and n not in doc
    )


def ask(path, meta):
    p = subprocess.Popen(
        [sys.executable, str(path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    msg = {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {"_meta": meta}}
    out, _ = p.communicate(json.dumps(msg) + "\n", timeout=60)
    return json.loads(out.splitlines()[0])


print("■ 1. 코드 줄 수")
for name, path in SERVERS.items():
    print(f"  {name:<12} {code_lines(path):>4}줄   {path.relative_to(ROOT)}")

print("\n■ 2. _meta에 버전만 실은 요청(15편 첫 클라이언트처럼)")
for name, path in SERVERS.items():
    r = ask(path, VERSION)
    print(
        f"  {name:<12} "
        + ("받아 줌" if "result" in r else f"거절 {r['error']['code']}: {r['error']['message'][:70]}")
    )

print("\n■ 3. 정식 _meta로 discover")
for name, path in SERVERS.items():
    res = ask(path, FULL)["result"]
    caps = ", ".join(res["capabilities"])
    print(
        f"  {name:<12} 버전 {res['supportedVersions']} · 기능 [{caps}] · 캐시 {res.get('cacheScope')}/{res.get('ttlMs')}"
    )
