"""과제 2 풀이: 같은 도구·같은 인자 반복 호출을 막고, 턴 수에 상한을 둔다. 막히면 "더 찾을 수 없음"을 결과로 알려 준다.
사용: uv run python sec02/solutions/a2_guard.py   → 성적표에 한 줄 추가"""

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import agent
from tools15 import run_tool

MAX_TURNS, MAX_CALLS = 5, 6


def run(question, trace=None, tools=agent.TOOLS, max_turns=MAX_TURNS, verbose=False):
    trace = trace or agent.Trace()
    messages = [
        {
            "role": "system",
            "content": "도구 결과로 답할 수 없으면 추측하지 말고 '공시 데이터로 확인되지 않음'이라고 답하라.",
        },
        {"role": "user", "content": question},
    ]
    seen = set()
    for _ in range(max_turns):
        reply = trace.llm(messages, tools)
        messages.append(reply)
        if not reply.get("tool_calls"):
            return reply.get("content") or ""
        for call in reply["tool_calls"]:
            name, args = call["function"]["name"], json.loads(call["function"]["arguments"] or "{}")
            key = (name, json.dumps(args, sort_keys=True, ensure_ascii=False))
            if key in seen:
                result = {
                    "error": "이미 같은 인자로 불렀습니다. 다른 도구가 없으면 확인되지 않는다고 답하세요."
                }
            elif len(trace.tools) >= MAX_CALLS:
                result = {"error": f"도구 호출 상한({MAX_CALLS}번)에 닿았습니다. 지금까지의 결과로 답하세요."}
            else:
                result = run_tool(name, args)
            seen.add(key)
            trace.tools.append((name, args, "error" in result))
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    return "(턴 상한)"


agent.run = run
spec = importlib.util.spec_from_file_location("h", HERE / "03_harness15.py")
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
h.run = run
h.main(f"과제2 · 반복 막기 + 상한 · {agent.MODEL.split('/')[-1]}")
