"""4편 ① 사업보고서 원문을 에이전트에게 어떻게 건넬까. 같은 질문 6개를 세 가지 방식으로 돌린다.
  A 전부 넣기        : read_full_report 하나 (원문 전체가 도구 결과로 들어간다)
  B 목차 + 섹션 통째 : list_sections → read_section (섹션 하나를 통째로)
  C 목차 + 상한 + 찾기: list_sections → read_section(한 번에 6,000자) + find_in_report
모델: deepseek-v4-flash (입력 100만 토큰당 $0.03, 100만 토큰까지 받는다 — 원문 전체 50만 토큰도 들어간다)
지표: 통과(정답 키), 호출마다 모델이 읽은 토큰, 합계 토큰, 비용, 시간 → data/context_runs.json
사용: uv run python sec04/01_context.py [A B C]
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec02"))
os.environ.setdefault("MODEL", "deepseek/deepseek-v4-flash")  # agent.py가 읽는다
import agent
import report_tools as rt
from report import load
from tools15 import ROOT

QIDS = ["q25", "q26", "q32", "q35", "q18", "q20"]
STRATEGIES = {
    "A": ("전부 넣기", ["read_full_report"], None),
    "B": ("목차 + 섹션 통째", ["list_sections", "read_section"], None),
    "C": ("목차 + 상한 + 찾기", ["list_sections", "read_section", "find_in_report"], 6000),
}
RULE = "원문 도구로 확인한 내용으로만 답하고, 숫자는 원문 그대로 적어 줘"


def flat(s):
    return "".join(s.split())


def run_strategy(label, names, cap, qids=QIDS, tool_fn=None):
    """질문들을 한 방식으로 돌려 행 목록을 돌려준다. tool_fn을 주면 run_tool 대신 쓴다(과제용)."""
    qs = {json.loads(line)["id"]: json.loads(line) for line in (ROOT / "eval" / "questions.jsonl").open()}
    answer_keys = json.loads((ROOT / "eval" / "answer_keys.json").read_text())
    for q in qids:  # 원문을 먼저 받아 둔다(회사마다 한 번, 수 MB)
        load(qs[q]["corp"], qs[q]["year"])
    agent.run_tool = tool_fn or rt.run_tool
    rt.CAP = cap

    def one(qid):
        q, tr, t0 = qs[qid], agent.Trace(), time.time()
        msg = f"{q['q']} ({q['corp']} {q['year']}년 사업보고서 기준. {RULE})"
        answer = agent.run(msg, tr, tools=rt.tools(*names), max_turns=10)
        ok = all(any(flat(k) in flat(answer) for k in g) for g in answer_keys[qid])
        return {
            "id": qid,
            "q": q["q"],
            "ok": ok,
            "calls": [c["tokens"] for c in tr.calls],
            "tools": [n for n, _, _ in tr.tools],
            "cost": sum(c["cost"] for c in tr.calls),
            "seconds": round(time.time() - t0, 1),
            "answer": answer[:400],
        }

    with ThreadPoolExecutor(3) as ex:
        return list(ex.map(one, qids))


def report(key, label, rows):
    tok = sum(sum(r["calls"]) for r in rows)
    print(
        f"\n■ {key} {label}: 통과 {sum(r['ok'] for r in rows)}/{len(rows)} · 토큰 {tok:,} · "
        f"${sum(r['cost'] for r in rows):.3f} · 문항당 {sum(r['seconds'] for r in rows) / len(rows):.0f}초"
    )
    for r in rows:
        bars = " ".join(f"{t / 1000:.0f}k" for t in r["calls"])
        print(f"  {'✅' if r['ok'] else '❌'} {r['q']:<28} 호출별 토큰 [{bars}]")


def main(keys):
    path = ROOT / "data" / "context_runs.json"
    out = json.loads(path.read_text()) if path.exists() else {}
    for key in keys:
        label, names, cap = STRATEGIES[key]
        rows = run_strategy(label, names, cap)
        out[key] = {"label": label, "rows": rows}
        report(key, label, rows)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("\n저장 → data/context_runs.json   막대: uv run python sec04/03_bars.py")


if __name__ == "__main__":
    main(sys.argv[1:] or list(STRATEGIES))
