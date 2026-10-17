"""과제 3 풀이: 15편 '예전 클라이언트'(initialize 핸드셰이크, 2025-11-25)를 SDK 서버에 붙여 본다.
SDK 서버의 discover는 새 버전(2026-07-28)만 알려 주지만, initialize로 오는 예전 클라이언트도 받는지 확인한다.
사용: uv run python sec16/solutions/a3_legacy_vs_sdk.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
legacy = ROOT / "sec15" / "solutions" / "a2_legacy_client.py"
for target in (ROOT / "sec15" / "server.py", ROOT / "sec16" / "server_sdk.py"):
    print(f"■ {target.relative_to(ROOT)}")
    out = subprocess.run(
        [sys.executable, str(legacy), str(target)], capture_output=True, check=False, text=True, timeout=120
    ).stdout
    print("\n".join("  " + line[:120] for line in out.splitlines()))
