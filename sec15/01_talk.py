"""15편 01: 클라이언트 흉내 — 서버를 띄우고 JSON-RPC 메시지를 한 줄씩 주고받는다.

Claude Code가 서버와 나누는 대화를 우리가 직접 해 본다: 무엇을 아니? → 도구 목록 → 도구 호출 → 틀린 버전.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
META = {  # 2026-07-28: 요청마다 버전 · 클라이언트 정보 · 클라이언트 기능을 _meta에 싣는다
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientInfo": {"name": "talk-15", "version": "0.1"},
    "io.modelcontextprotocol/clientCapabilities": {},
}


def short(obj, n=150):  # 한 줄에 들어가게 자른다
    s = json.dumps(obj, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + " …"


def payload(r):
    """결과 content의 글을 JSON으로 읽는다(SDK는 목록을 항목마다 content 하나로 나눠 보낸다)."""
    items = [json.loads(c["text"]) for c in r["result"]["content"]]
    return items[0] if len(items) == 1 else items


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else str(HERE / "server.py")  # 16편: SDK 서버도 같은 대화로
    p = subprocess.Popen(
        [sys.executable, target],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    def ask(n, method, params, label):
        msg = {"jsonrpc": "2.0", "id": n, "method": method, "params": params}
        t0 = time.time()
        p.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        p.stdin.flush()
        resp = json.loads(p.stdout.readline())
        print(f"\n■ {label}  ({time.time() - t0:.1f}초)")
        print("  →", short(msg))
        print("  ←", short(resp))
        return resp

    r = ask(1, "server/discover", {"_meta": META}, "1. 어떤 버전을 아니?")
    print("    지원 버전:", r["result"]["supportedVersions"])

    r = ask(2, "tools/list", {"_meta": META}, "2. 도구 목록")
    for t in r["result"]["tools"]:
        print(f"    - {t['name']}: {t['description'][:40]}")

    r = ask(
        3,
        "tools/call",
        {"name": "get_financials", "arguments": {"corp": "현대자동차"}, "_meta": META},
        "3. 도구 호출 — 현대자동차 재무",
    )
    data = payload(r)
    for k, v in data["accounts"].items():
        print(f"    {k}: 당기 {v['당기']}원 · 전기 {v['전기']}원")

    r = ask(
        4,
        "tools/call",
        {
            "name": "search_filings",
            "arguments": {"query": "관세 위험", "corp": "현대자동차", "k": 3},
            "_meta": META,
        },
        "4. 도구 호출 — 본문 검색 '관세 위험'",
    )
    for d in payload(r):
        print(f"    · {d['section']}")

    ask(
        5,
        "tools/list",
        {"_meta": {**META, "io.modelcontextprotocol/protocolVersion": "2024-11-05"}},
        "5. 모르는 버전으로 물으면",
    )
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    main()
