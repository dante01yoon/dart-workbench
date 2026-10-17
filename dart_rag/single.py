"""비교 기준: 도구를 직접 부르는 단일 에이전트 (강의 12편).
#1 강의의 while 루프 그대로 — 모델이 도구를 고르고, 결과를 보고, 더 부를지 끝낼지 정한다.
사용: python -m dart_rag.single "질문"
"""

import json
import os
import sys
import time
import urllib.request

from .web import web_search

TOOLS = [
    {"type": "function", "function": {"name": "search_report", "description": "사업보고서 본문 검색. 결과에 회사·연도·섹션 경로가 있다.",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "corp": {"type": "string"}, "year": {"type": "integer"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "get_financials", "description": "재무 API 연결 손익(매출액·영업이익·당기순이익), 원 단위.",
     "parameters": {"type": "object", "properties": {"corp": {"type": "string"}, "year": {"type": "integer"}}, "required": ["corp", "year"]}}},
    {"type": "function", "function": {"name": "web_search", "description": "최근 뉴스 검색.",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
]
SYSTEM = ("너는 한국 상장사 리서치 도우미다. 대상: 삼성전자·SK하이닉스·현대자동차·카카오 2024·2025 사업보고서. "
          "도구로 근거를 찾고, 답의 문장마다 (출처: 섹션 경로 또는 URL)를 붙여라. 투자 권유 금지.")


def call(name, args):
    from mcp_server.manual import call_tool

    if name == "web_search":
        return web_search(args["query"], k=5)
    return call_tool(name, {**args, "k": 5} if name == "search_report" else args)


def run(question, max_turns=10):
    t0, tokens, calls = time.time(), 0, []
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    for _ in range(max_turns):
        body = {"model": os.environ["MODEL"], "messages": msgs, "tools": TOOLS, "max_tokens": 4000}
        req = urllib.request.Request(os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"})
        r = json.load(urllib.request.urlopen(req, timeout=300))
        tokens += r.get("usage", {}).get("total_tokens", 0)
        m = r["choices"][0]["message"]
        msgs.append({k: v for k, v in m.items() if k in ("role", "content", "tool_calls")})
        if not m.get("tool_calls"):
            return {"answer": m.get("content", ""), "tokens": tokens, "seconds": round(time.time() - t0, 1), "calls": calls}
        for tc in m["tool_calls"]:
            args = json.loads(tc["function"]["arguments"] or "{}")
            try:
                out = call(tc["function"]["name"], args)
            except Exception as e:  # noqa: BLE001 — 도구 오류도 모델에게 보여 준다
                out = {"error": str(e)}
            calls.append({"t": round(time.time() - t0, 1), "tool": tc["function"]["name"], "args": args})
            msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(out, ensure_ascii=False)[:6000]})
    return {"answer": "(턴 상한 도달)", "tokens": tokens, "seconds": round(time.time() - t0, 1), "calls": calls}


if __name__ == "__main__":
    r = run(" ".join(sys.argv[1:]) or "삼성전자와 SK하이닉스의 2025년 메모리 사업 실적과 위험 요인을 비교해 줘")
    for c in r["calls"]:
        print(f"  {c['t']:6.1f}s {c['tool']} {json.dumps(c['args'], ensure_ascii=False)[:80]}")
    print("토큰:", r["tokens"], " 시간:", r["seconds"], "s\n", r["answer"][:1500])
