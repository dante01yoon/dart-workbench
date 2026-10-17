"""1편 ① 에이전트 루프 복습 — HTTP 요청만으로 (OpenRouter, OpenAI 호환 형식)."""

import json
import os
import sys
import urllib.request

from tools import TOOLS, get_financials

URL = os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions"
MODEL = os.environ.get("MODEL", "deepseek/deepseek-v4-pro")


def call_llm(messages):
    body = {"model": MODEL, "messages": messages, "tools": TOOLS}
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
            "Content-Type": "application/json",
        },
    )
    return json.load(urllib.request.urlopen(req, timeout=180))


def run(question, max_turns=6):
    messages = [{"role": "user", "content": question}]
    for turn in range(max_turns):
        reply = call_llm(messages)["choices"][0]["message"]
        messages.append(reply)
        if not reply.get("tool_calls"):  # 도구를 안 부르면 = 최종 답
            return reply["content"]
        for call in reply["tool_calls"]:
            args = json.loads(call["function"]["arguments"])
            print(f"  [턴 {turn + 1}] 도구 호출 get_financials({args})")
            try:
                result = get_financials(**args)
            except Exception as e:  # 실패도 결과로 돌려준다 → 모델이 고쳐서 다시 시도
                result = {"error": str(e)}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    return "(턴 한도 초과)"


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "SK하이닉스의 2025년 영업이익은 얼마야?"
    print("질문:", q)
    print("답:", run(q))
