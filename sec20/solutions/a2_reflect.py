"""과제 2 풀이: 반성 루프를 끄고 켜서 비교한다 — 같은 질문 3개 × (반성 없음 · 반성 1회), 심판 지지 비율 · 비용 · 시간.
서버 없이 Workbench를 바로 부른다. 결과: data/reflect_compare.json
uv run python sec20/solutions/a2_reflect.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from mcp_tools import McpTools
from workbench import Workbench

QS = [
    "카카오 2025년 실적과 사업 위험 요인을 정리해 줘",
    "삼성전자와 SK하이닉스의 2025년 영업이익과 메모리 사업 위험을 비교해 줘",
    "현대자동차 2025년 매출과 관세 관련 위험을 알려줘",
]
mcp = McpTools()
rows = []
for q in QS:
    for reflect in (False, True):
        wb = Workbench(mcp, emit=lambda e: None, cap=0.05)
        out = wb.research(q, reflect=reflect)
        ok = sum(s["badge"] == "지지" for s in out["report"])
        rows.append(
            {
                "q": q,
                "reflect": reflect,
                "ok": ok,
                "total": len(out["report"]),
                "spent": out["spent"],
                "seconds": out["seconds"],
            }
        )
        print(
            f"{'반성 1회' if reflect else '반성 없음'}  지지 {ok}/{len(out['report'])}  ${out['spent']}  "
            f"{out['seconds']}초  {q[:24]}",
            flush=True,
        )
mcp.close()
(HERE.parent / "data" / "reflect_compare.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
for r in (False, True):
    sub = [x for x in rows if x["reflect"] == r]
    print(
        f"\n{'반성 1회' if r else '반성 없음'}: 지지 {sum(x['ok'] for x in sub)}/{sum(x['total'] for x in sub)} · "
        f"${sum(x['spent'] for x in sub):.4f} · 평균 {sum(x['seconds'] for x in sub) / len(sub):.0f}초"
    )
