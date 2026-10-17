"""16편 03: 도구가 많은 MCP 서버를 Claude Code에 붙이면 — 도구 15개 · 40개 × 도구 검색 켬 · 끔.

3편에서 우리가 직접 만든 도구 검색을 Claude Code는 기본으로 한다(ToolSearch: 도구 이름만 먼저 보이고, 필요할 때 정의를 불러온다).
질문 20개(3편과 같다)마다 claude -p를 돌려 고른 도구 · 첫 호출 입력 토큰 · 턴 · 시간 · 비용을 잰다 → data/cc_tool_count.json
"""

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sec03"))
from select_lab import Q  # 3편 질문 20개 (질문, 정답 도구)

OUT = ROOT / "data" / "cc_tool_count.json"
CONFIGS = [(15, True), (15, False), (40, True), (40, False)]


def config_file(n):
    p = ROOT / "data" / f"mcp_tools{n}.json"
    cfg = {
        "mcpServers": {
            "dart": {
                "command": "uv",
                "args": ["run", "python", "sec16/tools_n.py"],
                "env": {"TOOLS_N": str(n)},
            }
        }
    }
    p.write_text(json.dumps(cfg))
    return p


def run(n, search, q, want):
    env = {**os.environ, "ENABLE_TOOL_SEARCH": "true" if search else "false"}
    cmd = [
        "claude",
        "-p",
        q,
        "--setting-sources",
        "project",
        "--strict-mcp-config",
        "--mcp-config",
        str(config_file(n)),
        "--model",
        "haiku",
        "--tools",
        "ToolSearch",
        "--allowedTools",
        "mcp__dart__*",
        "ToolSearch",
        "--output-format",
        "stream-json",
        "--verbose",
    ]
    t0 = time.time()
    out = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        capture_output=True,
        check=False,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=300,
    ).stdout
    ev = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    msgs = [e["message"] for e in ev if e.get("type") == "assistant"]
    uses = [c["name"] for m in msgs for c in m["content"] if c.get("type") == "tool_use"]
    picked = next((u.removeprefix("mcp__dart__") for u in uses if u.startswith("mcp__dart__")), None)
    u0 = msgs[0]["usage"] if msgs else {}
    end = ev[-1] if ev else {}
    return {
        "n": n,
        "search": search,
        "q": q,
        "want": want,
        "picked": picked,
        "ok": picked == want,
        "tool_search_calls": uses.count("ToolSearch"),
        "first_prompt": sum(
            u0.get(k, 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
        ),
        "turns": end.get("num_turns"),
        "sec": round(time.time() - t0, 1),
        "cost": end.get("total_cost_usd") or 0,
    }


def main():
    jobs = [(n, s, q, w) for n, s in CONFIGS for q, w in Q]
    print(f"claude -p {len(jobs)}번 (설정 4개 × 질문 {len(Q)}개, 4개씩 동시에)")
    rows = []
    with ThreadPoolExecutor(4) as ex:
        for r in ex.map(lambda j: run(*j), jobs):
            rows.append(r)
            if len(rows) % 10 == 0:
                print(f"  {len(rows)}/{len(jobs)}")
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print(
        f"\n{'도구':>4} {'도구 검색':>8} {'맞은 도구':>8} {'첫 입력 토큰':>10} {'평균 턴':>6} {'평균 시간':>8} {'비용':>8}"
    )
    for n, s in CONFIGS:
        g = [r for r in rows if r["n"] == n and r["search"] == s]
        ok = sum(r["ok"] for r in g)
        tok = sum(r["first_prompt"] for r in g) / len(g)
        turns = sum(r["turns"] or 0 for r in g) / len(g)
        sec = sum(r["sec"] for r in g) / len(g)
        print(
            f"{n:>5} {'켬' if s else '끔':>8} {ok:>6}/{len(g)} {tok:>12,.0f} {turns:>8.1f} {sec:>8.1f}초 ${sum(r['cost'] for r in g):.4f}"
        )
    miss = [r for r in rows if not r["ok"]]
    if miss:
        print("\n틀린 것:")
        for r in miss:
            print(
                f"  {r['n']}개 · 검색 {'켬' if r['search'] else '끔'} · {r['q']} → {r['picked']} (정답 {r['want']})"
            )
    print(f"\n저장 → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
