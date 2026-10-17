"""과제 3 풀이: 에이전트에 배당 도구(재무 API alotMatter)를 하나 더 주면? 배당 문항 3개(q33 · q34 · q38)를
본편 도구(검색 + 주요 계정)와 배당 도구를 더한 경우로 각각 풀어 정답 · 도구 호출을 비교한다.
사용: uv run python sec10/solutions/a3_dividend_tool.py"""

import importlib
import json

import _lab  # noqa: F401
from cite import run_tool

ag = importlib.import_module("03_agentic")  # 본편 에이전트(검색 · 주요 계정 도구, 채점 함수)를 그대로 쓴다
DIVIDENDS = {
    "type": "function",
    "function": {
        "name": "dividends",
        "description": "재무 API 배당: 주당 현금배당금 · 배당성향 · 시가배당률(당기 · 전기 · 전전기). 결과에 [API]를 붙여 인용한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "corp": {"type": "string", "enum": ag.CORPS},
                "year": {"type": "integer", "enum": [2024, 2025]},
            },
            "required": ["corp", "year"],
        },
    },
}


def agent2(q, max_turns=8):
    """본편 agent와 같은 루프에 dividends 분기만 더했다."""
    msgs = [
        {"role": "system", "content": ag.SYSTEM + "\n- 배당은 dividends(재무 API)를 쓴다."},
        {"role": "user", "content": q},
    ]
    calls, seen = [], []
    for _ in range(max_turns):
        m, _ = ag.llm(msgs)
        msgs.append({k: v for k, v in m.items() if k in ("role", "content", "tool_calls")})
        if not m.get("tool_calls"):
            return (m.get("content") or "").strip() or "(빈 답)", calls
        tc = m["tool_calls"][0]
        args, name = json.loads(tc["function"]["arguments"] or "{}"), tc["function"]["name"]
        calls.append(f"{name}({', '.join(str(v) for v in args.values())})")
        if name == "search_report":
            hits = ag.store.search(args.get("query", q), args.get("corp"), k=5)
            parts = []
            for i in hits:
                seen.append(i)
                parts.append(
                    f"[S{len(seen)}] ({ag.store.chunks[i]['section']})\n{ag.store.chunks[i]['text'][:1500]}"
                )
            result = "\n\n".join(parts)
        else:
            result = json.dumps(run_tool(name, args), ensure_ascii=False)
        msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
    return "(도구 호출 한도에서 멈춤)", calls


ag.TOOLS.append(DIVIDENDS)
for qid in ("q33", "q34", "q38"):
    q = ag.qs[qid]
    ag.TOOLS.remove(DIVIDENDS)
    before, c1, _ = ag.agent(ag.store, q["q"])
    ag.TOOLS.append(DIVIDENDS)
    after, c2 = agent2(q["q"])
    print(
        f"■ {q['q']}\n  본편 도구  {'✅' if ag.grade(qid, before) else '❌'} {c1}\n  + 배당 도구 {'✅' if ag.grade(qid, after) else '❌'} {c2}"
    )
