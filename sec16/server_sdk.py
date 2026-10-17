"""16편: 15편 서버를 공식 Python SDK(mcp 2.3, MCPServer)로 다시 쓴다.

- 도구: 함수에 데코레이터만 붙인다. 입력 스키마는 타입 힌트에서, 설명은 docstring에서 SDK가 만든다.
- 버전 확인, server/discover, 캐시 필드, 오류 응답은 SDK가 맡는다(15편에서 손으로 짠 부분).
- 새로 더하는 것: 리소스(보고서 목차) · 프롬프트(두 회사 비교 리포트)
"""

import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec15"))
import server as manual  # 15편 서버: 도구 본체(call_tool)를 그대로 쓴다
from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations

Corp = Literal["삼성전자", "SK하이닉스", "현대자동차", "카카오"]
READ_ONLY = ToolAnnotations(readOnlyHint=True)

mcp = MCPServer("dart-filings", version="0.2.0", instructions=manual.INSTRUCTIONS)


@mcp.tool(annotations=READ_ONLY)
def list_reports() -> list[dict]:
    """검색할 수 있는 사업보고서 목록(회사, 사업연도, 보고서 이름)을 돌려준다."""
    return manual.call_tool("list_reports", {})


@mcp.tool(annotations=READ_ONLY)
def get_financials(corp: Corp) -> dict:
    """재무 API 기준 연결 매출액 · 영업이익 · 당기순이익(당기 · 전기, 원)을 돌려준다. 숫자 질문은 본문 검색보다 이 도구가 정확하다."""
    return manual.call_tool("get_financials", {"corp": corp})


@mcp.tool(annotations=READ_ONLY)
def search_filings(query: str, corp: Corp | None = None, k: int = 5) -> list[dict]:
    """2025 사업보고서 본문에서 질문과 관련된 조각을 찾는다. 결과마다 회사 · 섹션 경로 · 원문을 준다. 답할 때 섹션 경로를 출처로 적는다."""
    return manual.call_tool("search_filings", {"query": query, "corp": corp, "k": k})


def toc(corp: str) -> str:
    """보고서 목차: 섹션 경로의 앞 두 단계만 순서대로."""
    seen = []
    for c in manual.store().chunks:
        top = " > ".join(c["section"].split(" > ")[:2])
        if c["corp"] == corp and top not in seen:
            seen.append(top)
    return "\n".join(seen)


def toc_resource(corp):
    """회사마다 리소스 하나: Claude Code의 @ 목록에 바로 뜬다."""

    def read() -> str:
        return toc(corp)

    mcp.resource(
        f"dart://toc/{corp}",
        name=f"{corp} 목차",
        mime_type="text/plain",
        description=f"{corp} 2025 사업보고서 목차(섹션 경로)",
    )(read)


for _corp in manual.CORPS:
    toc_resource(_corp)


@mcp.prompt(title="두 회사 비교 리포트")
def compare_companies(corp_a: str, corp_b: str, topic: str = "수익성과 위험 요인") -> str:
    """두 회사의 2025 사업보고서를 같은 기준으로 비교하는 리포트를 쓰게 한다."""
    return (
        f"{corp_a}와 {corp_b}의 2025 사업보고서로 '{topic}'을 비교해 줘.\n"
        "1) 숫자는 get_financials로 가져오고, 2) 서술은 search_filings로 회사마다 따로 찾고,\n"
        "3) 문장마다 (회사 · 섹션 경로) 출처를 달고, 4) 투자 권유는 하지 마. 표 하나로 끝내."
    )


if __name__ == "__main__":
    mcp.run()
