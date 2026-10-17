"""16편 실험용 서버: 15편 손 구현 서버에 3편 도구(15개 또는 40개)를 MCP 도구로 붙인다.
TOOLS_N=15 또는 40. 미끼 도구는 부르면 "연결되지 않음"을 돌려준다(3편과 같다).
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sec15"))
sys.path.insert(0, str(ROOT / "sec03"))
import server
import tools40

N = int(os.environ.get("TOOLS_N", "15"))
SRC = tools40.TOOLS15 if N == 15 else tools40.TOOLS40
server.TOOLS[:] = [
    {
        "name": t["function"]["name"],
        "description": t["function"]["description"],
        "inputSchema": t["function"]["parameters"],
    }
    for t in SRC
]
server.call_tool = lambda name, args: tools40.run_tool(name, args)

if os.environ.get("BETTER_DESC"):  # 과제 1: 도구 검색이 찾기 쉽게 서버 안내문과 설명에 쓰임새를 적는다
    server.INSTRUCTIONS = (
        "DART 공시 도구 서버. 매출액 · 영업이익 · 순이익 · 자산총계 같은 한 회사의 대표 숫자는 key_accounts, "
        "대표이사 · 본사 주소 · 설립일은 company_info, 영업이익률 · ROE 같은 비율은 financial_ratios를 먼저 쓴다. "
        "세부 계정(재고자산 · 감가상각 등)만 all_financial_statements."
    )
    EXTRA = {
        "key_accounts": " 영업이익 · 매출 · 자산총계를 물으면 이 도구가 가장 빠르고 정확하다.",
        "company_info": " 대표이사(CEO)가 누구인지, 본사 주소를 물으면 이 도구.",
        "all_financial_statements": " 대표 숫자(영업이익 · 자산총계)는 key_accounts를 먼저 쓴다.",
    }
    for t in server.TOOLS:
        t["description"] += EXTRA.get(t["name"], "")

if __name__ == "__main__":
    server.main()
