"""공시 검색 MCP 서버 — 공식 Python SDK(mcp 2.x, MCPServer) 버전 (강의 16편).

15편 손 구현(manual.py)과 같은 도구를 데코레이터로 다시 쓰고, 리소스·프롬프트를 더한다.
프로토콜 버전 협상, 캐시 필드, 스키마 생성은 SDK가 맡는다.
실행: .venv/bin/python mcp_server/sdk.py            (stdio)
      .venv/bin/python mcp_server/sdk.py --http     (Streamable HTTP, 17편)
"""

import json
import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp_types import ToolAnnotations  # noqa: E402

from dart_rag import dart  # noqa: E402
from mcp_server import manual  # noqa: E402  (도구 본체는 15편 코드를 그대로 쓴다)

Corp = Literal["삼성전자", "SK하이닉스", "현대자동차", "카카오"]
Year = Literal[2024, 2025]
READ_ONLY = ToolAnnotations(readOnlyHint=True)

server = MCPServer("dart-filings", version="0.2.0", instructions=manual.INSTRUCTIONS)


@server.tool(annotations=READ_ONLY)
def list_reports() -> list[dict]:
    """검색할 수 있는 사업보고서 목록(회사, 사업연도, 접수번호)을 돌려준다."""
    return manual.call_tool("list_reports", {})


@server.tool(annotations=READ_ONLY)
def get_financials(corp: Corp, year: Year) -> dict:
    """재무 API(XBRL) 기준 연결 손익 숫자를 원 단위로 돌려준다. 매출액·영업이익·당기순이익 질문은 본문 검색보다 이 도구가 정확하다."""
    return manual.call_tool("get_financials", {"corp": corp, "year": year})


@server.tool(annotations=READ_ONLY)
def search_report(query: str, corp: Corp | None = None, year: Year | None = None, k: int = 5) -> list[dict]:
    """사업보고서 본문에서 질문과 관련된 조각을 찾는다. 결과마다 회사·연도·섹션 경로와 원문을 준다. 답할 때 섹션 경로를 출처로 적는다."""
    return manual.call_tool("search_report", {"query": query, "corp": corp, "year": year, "k": max(1, min(k, 10))})


@server.resource("dart://reports", mime_type="application/json", description="수집된 사업보고서 목록")
def reports() -> str:
    return json.dumps(manual.call_tool("list_reports", {}), ensure_ascii=False)


@server.resource("dart://toc/{corp}/{year}", mime_type="text/plain", description="한 보고서의 목차(섹션 경로)")
def toc(corp: str, year: str) -> str:
    seen = []
    for c in manual.searcher().chunks:
        if c["corp"] == corp and str(c["year"]) == year and c["section"] not in seen:
            seen.append(c["section"])
    return "\n".join(seen) or f"{corp} {year} 보고서가 없습니다"


@server.prompt(title="두 회사 비교 리포트")
def compare_companies(corp_a: str, corp_b: str, topic: str = "수익성과 위험 요인") -> str:
    """두 회사의 사업보고서를 같은 기준으로 비교하는 리포트를 쓰게 한다."""
    return (f"{corp_a}와 {corp_b}의 2025 사업보고서로 '{topic}'을 비교해 줘.\n"
            "1) 숫자는 get_financials로 가져오고, 2) 서술은 search_report로 회사마다 따로 찾고,\n"
            "3) 문장마다 (회사 · 섹션 경로) 출처를 달고, 4) 투자 권유는 하지 마.")


if __name__ == "__main__":
    if "--http" in sys.argv:
        server.run("streamable-http")
    else:
        server.run()

_ = dart  # dart_rag.dart가 .env를 읽는다(import 부수효과)
