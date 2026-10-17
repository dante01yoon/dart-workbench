"""과제 3 풀이: 내 토큰을 하나 만든다 — 원문은 .env에만 저장하고, 서버(Render 대시보드)에 넣을 줄은 sha256 해시로 만든다.
화면에는 토큰 원문을 찍지 않는다.
사용: uv run python sec17/solutions/a3_make_token.py 이름 https://<내 주소>/mcp
"""

import hashlib
import secrets
import sys
from pathlib import Path

ENV = Path(__file__).resolve().parent.parent.parent / ".env"
name = sys.argv[1] if len(sys.argv) > 1 else "me"
resource = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8790/mcp"
var = f"MCP_TOKEN_{name.upper()}"

token = secrets.token_urlsafe(32)  # 256비트 무작위
with ENV.open("a") as f:
    f.write(f"\n{var}={token}\n")
digest = hashlib.sha256(token.encode()).hexdigest()
print(f".env에 {var} 저장(원문은 화면에 찍지 않음)")
print("서버 MCP_TOKENS에 넣을 줄(해시만):")
print(f"  {name};sha256:{digest};dart:read;{resource}")
