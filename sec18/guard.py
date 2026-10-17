"""18편 guard: Claude Code와 MCP 서버 사이에 끼우는 검문소(stdio 중계). 클라이언트 쪽에서 세 가지를 막는다.

1. 허용 목록: policy.json에 적힌 도구만 통과
2. 최소 권한: read_only면 readOnlyHint가 없는 도구(쓰기 · 지우기)는 통과시키지 않는다
3. 설명 고정: 처음 확인한 도구 정의(이름 · 설명 · 입력 형식)의 sha256을 data/mcp_pins.json에 고정 → 바뀌면 막는다
막은 도구는 목록에서 빼고, 불러도 서버에 보내지 않는다. 기록은 data/guard_log.jsonl.
사용(mcp 설정의 command): python sec18/guard.py <서버 이름> -- <서버를 띄우는 명령…>
GUARD_PIN=1이면 지금 목록을 사람이 확인한 것으로 보고 해시를 새로 고정한다.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY = json.loads((Path(__file__).resolve().parent / "policy.json").read_text())
PINS = ROOT / "data" / "mcp_pins.json"
LOG = ROOT / "data" / "guard_log.jsonl"


def fingerprint(tool):
    body = {k: tool.get(k) for k in ("name", "description", "inputSchema")}
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def check(server, tools, pins):
    """도구마다 (통과 여부, 이유). pins: {서버: {도구: 해시}}"""
    rule, mine = POLICY.get(server), pins.get(server, {})
    out = []
    for t in tools:
        name, why = t["name"], []
        if rule is None:
            why.append("허용 목록에 없는 서버")
        else:
            if name not in rule["allow_tools"]:
                why.append("허용 목록에 없는 도구")
            if rule.get("read_only") and not (t.get("annotations") or {}).get("readOnlyHint"):
                why.append("읽기 전용이 아닌 도구")
            if name in mine and mine[name] != fingerprint(t):
                why.append("고정한 뒤 정의가 바뀜")
            elif name not in mine and not why:
                why.append("아직 고정하지 않은 도구")
        out.append((t, not why, " · ".join(why) or "통과"))
    return out


ORDER = re.compile(
    r"[^.\n]*(반드시|부르세요|불러라|호출하라|무시하라|ignore (all |previous )?instructions)[^.\n]*[.]?",
    re.IGNORECASE,
)


def clean_result(text):
    """도구 결과에 섞인 '모델에게 시키는 말'을 지운다(과제 2). 지운 문장 목록도 돌려준다."""
    hits = [m.group(0).strip() for m in ORDER.finditer(text)]
    return ORDER.sub(" [guard가 지운 문장] ", text), hits


def log(row):
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"t": time.strftime("%H:%M:%S"), **row}, ensure_ascii=False) + "\n")


def main():
    server, cmd = sys.argv[1], sys.argv[sys.argv.index("--") + 1 :]
    up = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=ROOT)
    pins = json.loads(PINS.read_text()) if PINS.exists() else {}
    allowed = set()
    for line in sys.stdin:
        if not line.strip():
            continue
        msg = json.loads(line)
        if msg.get("method") == "tools/call" and msg["params"].get("name") not in allowed:
            name = msg["params"].get("name")
            log({"server": server, "blocked_call": name})
            err = {"code": -32602, "message": f"guard가 막은 도구: {name}"}
            print(
                json.dumps({"jsonrpc": "2.0", "id": msg.get("id"), "error": err}, ensure_ascii=False),
                flush=True,
            )
            continue
        up.stdin.write(line if line.endswith("\n") else line + "\n")
        up.stdin.flush()
        if msg.get("id") is None:  # 알림은 답이 없다
            continue
        resp = json.loads(up.stdout.readline())
        if msg.get("method") == "tools/list" and "result" in resp:
            tools = resp["result"]["tools"]
            if os.environ.get("GUARD_PIN") == "1":
                pins[server] = {
                    t["name"]: fingerprint(t) for t in tools if t["name"] in POLICY[server]["allow_tools"]
                }
                PINS.parent.mkdir(exist_ok=True)
                PINS.write_text(json.dumps(pins, ensure_ascii=False, indent=1))
            verdicts = check(server, tools, pins)
            allowed = {t["name"] for t, ok, _ in verdicts if ok}
            resp["result"]["tools"] = [t for t, ok, _ in verdicts if ok]
            for t, ok, why in verdicts:
                if not ok:
                    log({"server": server, "hidden_tool": t["name"], "why": why})
                    print(f"[guard] {t['name']} 숨김 — {why}", file=sys.stderr, flush=True)
        if msg.get("method") == "tools/call" and os.environ.get("GUARD_RESULT") == "1" and "result" in resp:
            for c in resp["result"].get("content", []):
                if c.get("type") == "text":
                    c["text"], hits = clean_result(c["text"])
                    if hits:
                        log({"server": server, "cleaned": msg["params"]["name"], "n": len(hits)})
        print(json.dumps(resp, ensure_ascii=False), flush=True)
    up.terminate()


if __name__ == "__main__":
    main()
