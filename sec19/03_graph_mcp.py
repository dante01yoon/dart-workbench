"""19편 03: 14편 LangGraph 리서치 팀의 공시 · 재무 담당을 내 MCP 서버 도구로 바꾼다.

- 그래프(planner → worker × N 병렬 → writer)와 프롬프트는 14편 그대로. 바뀐 건 워커가 근거를 가져오는 곳뿐.
- 재무 담당: MCP get_financials, 공시 담당: MCP search_filings → 12편 근거 추출(LLM)은 그대로.
- 뉴스 담당은 그대로(Tavily). 사람 승인은 자동 통과.
uv run --no-project --with-requirements sec19/requirements.txt python sec19/03_graph_mcp.py ["질문"]
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

os.environ["AUTO_APPROVE"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec14"))
import graph  # 14편 그래프 · 12편 팀
from env import DART
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

Q = " ".join(sys.argv[1:]) or "카카오 2025년 실적과 사업 위험 요인을 정리해 줘"
CALLS = []


def blocks(content):  # 도구 결과 → 파이썬 값 (목록 결과는 항목마다 text 블록 하나)
    items = [content] if isinstance(content, str) else [c["text"] for c in content if c.get("type") == "text"]
    vals = [json.loads(x) for x in items]
    return vals[0] if len(vals) == 1 else vals


async def main():
    loop = asyncio.get_running_loop()
    async with MultiServerMCPClient({"dart": DART}).session("dart") as s:
        tools = {t.name: t for t in await load_mcp_tools(s)}

        def mcp(name, args):  # 그래프 워커는 스레드에서 돈다 → 이벤트 루프에 맡기고 기다린다
            t0 = time.time()
            out = asyncio.run_coroutine_threadsafe(tools[name].ainvoke(args), loop).result()
            CALLS.append(f"{name}({args.get('corp')}) {time.time() - t0:.2f}초")
            return blocks(out)

        def w_financials(t):
            fin = mcp("get_financials", {"corp": t["corp"]})
            ev = []
            for acc, v in fin["accounts"].items():
                quote = f"{acc} 당기 {v['당기']}원 / 전기 {v['전기']}원"
                ev.append(
                    {
                        "claim": f"{t['corp']} 2025년 연결 {acc} {v['당기']}원(전년 {v['전기']}원)",
                        "source": f"MCP get_financials · {fin['source']}",
                        "quote": quote,
                        "kind": "재무",
                        "text": quote,
                    }
                )
            return ev, 0.0

        def w_filings(t):
            hits = mcp("search_filings", {"query": t["query"], "corp": t.get("corp"), "k": 6})
            docs = [
                {"kind": "공시", "source": f"{h['corp']} 2025 사업보고서 · {h['section']}", "text": h["text"]}
                for h in (hits if isinstance(hits, list) else [hits])
            ]
            return graph.TEAM.extract(t, docs)

        graph.TEAM.w_financials, graph.TEAM.w_filings = w_financials, w_filings
        app = graph.build()
        print(f"■ 질문: {Q}\n")
        t0, report, ev = time.time(), [], []
        async for step in app.astream({"question": Q}, stream_mode="updates"):
            for node, out in (step or {}).items():
                what = ""
                if node == "planner":
                    what = " · ".join(f"{t['worker']}({t.get('corp') or '-'})" for t in out.get("tasks", []))
                elif node == "worker":
                    ev += out["evidence"]
                    what = f"근거 {len(out['evidence'])}개"
                elif node == "writer":
                    report = out["report"]
                    what = f"보고서 {len(report)}문장"
                print(f"  {time.time() - t0:5.1f}초  {node:8s} {what}", flush=True)
    print("\n■ MCP 호출:", " · ".join(CALLS))
    print(f"■ 근거 {len(ev)}개 중 원문 대조 통과 {sum(e['verified'] for e in ev)}개\n")
    for r in report:
        print(f"  {'●' if r['cites'] else '○'} {r['sentence']} {r['cites']}")


asyncio.run(main())
