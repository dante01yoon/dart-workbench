"""2편 에이전트: 1편 루프와 같고, 도구만 15개로 늘었다. Trace로 토큰·비용·시간을 함께 잰다."""

import json
import os
import time
import urllib.request

from tools15 import TOOLS, run_tool

URL = os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions"
MODEL = os.environ.get("MODEL", "deepseek/deepseek-v4-pro")


class Trace:
    def __init__(self):
        self.calls, self.tools = [], []

    def llm(self, messages, tools):
        body = {"model": MODEL, "messages": messages, "tools": tools, "usage": {"include": True}}
        req = urllib.request.Request(
            URL,
            data=json.dumps(body).encode(),
            headers={
                "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                "Content-Type": "application/json",
            },
        )
        t0 = time.time()
        r = json.load(urllib.request.urlopen(req, timeout=600))
        u = r.get("usage", {})
        self.calls.append(
            {"seconds": time.time() - t0, "tokens": u.get("total_tokens", 0), "cost": u.get("cost", 0)}
        )
        return r["choices"][0]["message"]


def run(question, trace=None, tools=TOOLS, max_turns=8, verbose=False):
    trace = trace or Trace()
    messages = [{"role": "user", "content": question}]
    for turn in range(max_turns):
        reply = trace.llm(messages, tools)
        messages.append(reply)
        if not reply.get("tool_calls"):
            return reply.get("content") or ""
        for call in reply["tool_calls"]:
            name, args = call["function"]["name"], json.loads(call["function"]["arguments"] or "{}")
            result = run_tool(name, args)
            trace.tools.append((name, args, "error" in result))
            if verbose:
                mark = "⚠️ 인자 오류 → 다시" if "error" in result else "✓"
                print(f"  [턴 {turn + 1}] {name}({json.dumps(args, ensure_ascii=False)}) {mark}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    return "(턴 한도 초과)"
