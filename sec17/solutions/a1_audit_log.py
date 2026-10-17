"""과제 1 풀이: 누가 어떤 도구를 불렀는지 기록한다 — 토큰마다 이름(client_id)이 있으니, 도구가 불릴 때 그 이름을 남긴다.
토큰 값은 기록하지 않는다. 로그: data/mcp_audit.jsonl
사용: uv run python sec17/solutions/a1_audit_log.py   (서버가 8790에서 뜬다 → 01_auth_test.py를 돌리고 로그를 본다)
"""

import functools
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import server_remote
from mcp.server.auth.middleware.auth_context import get_access_token

LOG = HERE.parent.parent / "data" / "mcp_audit.jsonl"


def audited(fn):
    @functools.wraps(fn)  # 이름 · 타입 힌트 · docstring을 그대로 → SDK가 같은 스키마를 만든다
    def run(*args, **kwargs):
        tok = get_access_token()
        row = {
            "t": time.strftime("%H:%M:%S"),
            "client": tok.client_id if tok else None,
            "scopes": tok.scopes if tok else None,
            "tool": fn.__name__,
            "args": kwargs,
        }
        with LOG.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return fn(*args, **kwargs)

    return run


if __name__ == "__main__":
    server_remote.build(wrap=audited).run("streamable-http", host=server_remote.HOST, port=server_remote.PORT)
