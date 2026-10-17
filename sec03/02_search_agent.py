"""3편 ② 도구 검색을 에이전트에게 맡기기. 처음엔 find_tools 하나만 보여 주고,
에이전트가 검색해서 고른 도구만 다음 턴부터 붙인다. 도구 40개 설명을 매번 다 보내지 않는다.
사용: uv run python sec03/02_search_agent.py "질문"        (비교: --all 을 붙이면 40개를 처음부터 다 보여 준다)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec02"))
from agent import Trace
from tool_search import ToolSearch
from tools40 import TOOLS40, run_tool

SEARCH = ToolSearch(TOOLS40)
BY_NAME = {t["function"]["name"]: t for t in TOOLS40}
FIND_TOOLS = {
    "type": "function",
    "function": {
        "name": "find_tools",
        "description": "필요한 공시 조회 도구를 찾는다. 찾고 싶은 내용을 짧게 넣으면(예: '배당금', '직원 연봉') "
        "가까운 도구 5개의 이름과 설명을 돌려주고, 그 도구들을 다음 턴부터 쓸 수 있게 된다.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}


def run(question, trace=None, max_turns=8, use_search=True):
    trace = trace or Trace()
    messages = [{"role": "user", "content": question}]
    loaded = {} if use_search else dict(BY_NAME)  # 지금까지 찾아서 붙인 도구
    for turn in range(max_turns):
        tools = [FIND_TOOLS, *loaded.values()] if use_search else list(loaded.values())
        reply = trace.llm(messages, tools)
        tok = trace.calls[-1]["tokens"]
        print(f"[턴 {turn + 1}] 보여 준 도구 {len(tools)}개 · 이번 호출 토큰 {tok:,}")
        messages.append(reply)
        if not reply.get("tool_calls"):
            return reply.get("content") or ""
        for call in reply["tool_calls"]:
            name, args = call["function"]["name"], json.loads(call["function"]["arguments"] or "{}")
            if name == "find_tools":
                found = SEARCH.search(args["query"], 5)
                loaded.update({t["function"]["name"]: t for t in found})
                result = [
                    {"name": t["function"]["name"], "description": t["function"]["description"]}
                    for t in found
                ]
                print(f"   find_tools({args['query']!r}) → {', '.join(r['name'] for r in result)}")
            elif name in loaded:
                result = run_tool(name, args)
                print(f"   {name}({json.dumps(args, ensure_ascii=False)})")
            else:
                result = {"error": f"{name}은(는) 아직 찾지 않은 도구입니다. find_tools로 먼저 찾으세요."}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    return "(턴 한도 초과)"


if __name__ == "__main__":
    use_search = "--all" not in sys.argv
    q = (
        " ".join(a for a in sys.argv[1:] if a != "--all")
        or "카카오 2025년 배당성향이랑 직원 1인 평균 급여 알려줘"
    )
    print("질문:", q, "\n")
    tr = Trace()
    answer = run(q, tr, use_search=use_search)
    print("\n답:", answer)
    print(
        f"\n합계: 호출 {len(tr.calls)}번 · 토큰 {sum(c['tokens'] for c in tr.calls):,} · ${sum(c['cost'] for c in tr.calls):.5f}"
    )
