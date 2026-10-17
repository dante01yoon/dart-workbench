"""과제 3 풀이: 증자·감자 현황 도구(irdsSttus)를 하나 더한다. 좋은 설명의 네 가지를 지킨다.
함정: 이 API는 최근 5년 치를 날짜 오름차순으로 준다(카카오 69줄). 앞 25줄만 자르면 2025년이 통째로 빠져
모델이 "2025년엔 없다"고 틀리게 답한다. 그래서 자르기 전에 요청한 연도로 거른다.
사용: uv run python sec02/solutions/a3_irds.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import agent
import tools15

tools15.SPEC.append(
    (
        "capital_changes",
        "irdsSttus.json",
        tools15.CorpYear,
        (
            "증자·감자 현황: 주식을 새로 발행(유상·무상증자, 주식매수선택권 행사 등)하거나 줄인(감자·소각) 날짜, 형태, 주식 종류, 수량, 1주당 액면가와 발행가(원). "
            "자기주식 취득·처분 수량은 treasury_stock을 쓴다. corp는 삼성전자·SK하이닉스·현대자동차·카카오, year는 2024 또는 2025."
        ),
        "증자",
        [
            "isu_dcrs_de",
            "isu_dcrs_stle",
            "isu_dcrs_stock_knd",
            "isu_dcrs_qy",
            "isu_dcrs_mstvdv_fval_amount",
            "isu_dcrs_mstvdv_amount",
        ],
    )
)
tools15._BY_NAME["capital_changes"] = tools15.SPEC[-1]
_orig = tools15.run_tool


def run_tool(name, args):
    if name != "capital_changes":
        return _orig(name, args)
    keep, tools15.MAX_ROWS = tools15.MAX_ROWS, 10_000  # 다 받아서
    try:
        r = _orig(name, args)
    finally:
        tools15.MAX_ROWS = keep
    if "rows" not in r:
        return r
    rows = [x for x in r["rows"] if x["isu_dcrs_de"].startswith(str(args["year"]))]  # 요청 연도만 남기고
    return {"rows": rows[:keep], "total": len(rows)}  # 그다음 자른다


tools15.run_tool = agent.run_tool = run_tool
TOOLS = tools15.TOOLS + [tools15._tool("capital_changes", tools15.CorpYear, tools15.SPEC[-1][3])]

print("도구 결과 직접 확인:", run_tool("capital_changes", {"corp": "카카오", "year": 2025}))
q = "카카오는 2025년에 증자나 감자를 한 적이 있어?"
print("\n질문:", q)
print("답:", agent.run(q, tools=TOOLS, verbose=True))
