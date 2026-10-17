"""18편 공용: 시험 서버를 시나리오별로 띄워 도구 목록만 받아 온다(모델 없음, 내 컴퓨터 안에서만)."""

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
META = {"io.modelcontextprotocol/protocolVersion": "2026-07-28"}


def list_tools(scenario):
    p = subprocess.Popen(
        [sys.executable, str(HERE / "test_server.py")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        env={**os.environ, "DEMO_SCENARIO": scenario},
    )
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": META}}
    out, _ = p.communicate(json.dumps(req) + "\n", timeout=60)
    return json.loads(out.splitlines()[0])["result"]["tools"]
