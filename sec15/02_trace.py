"""15편 02: Claude Code가 우리 서버에 보낸 요청을 순서대로 본다(MCP_TRACE 기록 파일).

uv run python sec15/02_trace.py data/mcp_trace.jsonl
"""

import json
import sys
from collections import Counter

path = sys.argv[1] if len(sys.argv) > 1 else "data/mcp_trace.jsonl"
with open(path, encoding="utf-8") as f:
    rows = [json.loads(line) for line in f]
print(f"{path} — 요청 {len(rows)}개\n")
for n, r in enumerate(rows, 1):
    m, out = r["in"], r["out"] or {}
    params = m.get("params") or {}
    what = m.get("method", "")
    if what == "tools/call":
        what += f"  {params.get('name')}  {json.dumps(params.get('arguments'), ensure_ascii=False)}"
    res = out.get("result") or {}
    if "error" in out:
        tail = f"오류 {out['error']['code']}"
    elif "tools" in res:
        tail = f"도구 {len(res['tools'])}개 · 캐시 필드 {'있음' if 'ttlMs' in res else '없음'}"
    elif "content" in res:
        tail = f"결과 {len(res['content'][0]['text']):,}자"
    else:
        tail = "확인"
    print(f"{n:>2}. {what[:90]}  →  {tail}")

c = Counter(r["in"].get("method") for r in rows)
print("\n합계:", " · ".join(f"{k} {v}번" for k, v in c.items()))
