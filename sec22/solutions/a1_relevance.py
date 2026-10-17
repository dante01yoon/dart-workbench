"""과제 1 풀이: 심판에 "질문에 맞는 답인가" 기준을 더한다 — 문장이 사실이어도 질문과 상관없으면 답을 "확인되지 않음"으로 바꾼다.
2027년 전망(q51) · 신차 출시일(q54)처럼 공시에 없는 걸 묻는 질문으로 시험한다.
사용: uv run python sec22/solutions/a1_relevance.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
for p in ("sec20", "sec12", "sec10"):
    sys.path.insert(0, str(ROOT / p))
from cite import questions
from mcp_tools import McpTools
from team import chat, parse
from workbench import Workbench

RELEVANT = """[질문]에 [보고서]가 직접 답하는지 판정하라. 문장이 사실이어도 질문이 묻는 것(연도 · 대상 · 항목)과 다르면 false.
JSON만: {"answers": true, "reason": "한 문장"}"""
NONE = "공시(2025 사업보고서)에서 확인되지 않습니다."


def research_checked(wb, q):
    r = wb.research(q)
    if r.get("refused") or not r["report"]:
        return r, None
    text = "\n".join(s["sentence"] for s in r["report"])
    raw, u = chat(f"{RELEVANT}\n\n[질문] {q}\n\n[보고서]\n{text}", max_tokens=2000)
    wb.charge(float(u.get("cost") or 0))
    v = parse(raw)
    if v.get("answers") is False:  # 질문과 상관없는 답 → 확인되지 않음으로
        r = {
            **r,
            "report": [{"sentence": NONE, "cites": [], "badge": "확인 안 됨", "reason": v.get("reason", "")}],
        }
    return r, v


qs, mcp = questions(), McpTools()
for qid in ("q51", "q54", "q01"):  # q01은 정상 답이 그대로 남는지 확인용
    wb = Workbench(mcp, emit=lambda e: None)
    r, v = research_checked(wb, qs[qid]["q"])
    print(f"{qid} {qs[qid]['q']}")
    print(f"   관련성 {v}  · ${wb.spent:.4f}")
    for s in r["report"]:
        print(f"   [{s['badge']}] {s['sentence'][:70]}")
mcp.close()
