"""19편 공용: .env 읽기 · 모델 · 서버 설정. 어댑터 전용 환경에서 돈다(tools15를 import하지 않는다)."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

MODEL = os.environ.get("MODEL_AGENT", "deepseek/deepseek-v4-flash")
# 16편 SDK 서버(mcp 2.3)는 실습 .venv에서 띄운다 → 어댑터(mcp 1.30)와 환경이 따로다
DART = {
    "transport": "stdio",
    "command": "uv",
    "args": ["run", "-q", "python", "sec16/server_sdk.py"],
    "cwd": str(ROOT),
}
SYSTEM = (
    "한국 상장사 2025 사업보고서 도우미. 숫자는 get_financials, 서술은 search_filings로 찾는다. "
    "문장마다 출처(재무 API 또는 섹션 경로)를 적고, 투자 권유는 하지 않는다."
)


def llm():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=MODEL,
        base_url=os.environ["OPENAI_BASE_URL"],
        api_key=os.environ["OPENAI_API_KEY"],
        max_tokens=6000,
    )
