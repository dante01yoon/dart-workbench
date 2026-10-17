"""1편 ② 같은 루프를 OpenAI 공식 SDK로 — base_url만 OpenRouter로 바꾸면 된다."""

import json
import os
import sys

from openai import OpenAI
from tools import TOOLS, get_financials

client = OpenAI(base_url=os.environ["OPENAI_BASE_URL"], api_key=os.environ["OPENAI_API_KEY"])
MODEL = os.environ.get("MODEL", "deepseek/deepseek-v4-pro")


def run(question, max_turns=6):
    messages = [{"role": "user", "content": question}]
    for _ in range(max_turns):
        reply = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS).choices[0].message
        messages.append(reply)
        if not reply.tool_calls:
            return reply.content
        for call in reply.tool_calls:
            result = get_financials(**json.loads(call.function.arguments))
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    return "(턴 한도 초과)"


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "현대자동차의 2025년 매출액은?"
    print("질문:", q)
    print("답:", run(q))
