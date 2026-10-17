"""12편 공용: 비교 기준 — 도구를 직접 부르는 단일 에이전트(1편 루프 그대로).

한 모델이 공시 검색 · 재무 API · 뉴스 검색 도구를 골라 부르고, 결과를 보고, 더 부를지 끝낼지 정한다.
5편 하네스처럼 한 턴에 도구 하나만 실행한다.
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec10"))
from cite import run_tool
from search import MODEL
from web import fetch_page, web_search

CORPS = ["삼성전자", "SK하이닉스", "현대자동차", "카카오"]
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_report",
            "description": "2025년 사업보고서 본문 검색. 결과에 회사 · 섹션 경로가 붙는다.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}, "corp": {"type": "string", "enum": CORPS}},
                "required": ["query", "corp"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "key_accounts",
            "description": "재무 API 주요 계정(연결): 매출액 · 영업이익 · 당기순이익, 원 단위.",
            "parameters": {
                "type": "object",
                "properties": {"corp": {"type": "string", "enum": CORPS}},
                "required": ["corp"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "news",
            "description": "최근 뉴스 검색. 상위 기사 3개의 제목 · 날짜 · 본문 앞부분.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]
SYSTEM = (
    "너는 한국 상장사 리서치 도우미다. 대상: 삼성전자 · SK하이닉스 · 현대자동차 · 카카오. "
    "도구로 근거를 찾고, 답의 문장마다 (출처: 섹션 경로 · 재무 API · 기사 제목)를 붙여라. 투자 권유 금지."
)


def call(name, args, store):
    if name == "search_report":
        ids = store.search(args.get("query", ""), args.get("corp"), k=5)
        return [{"source": store.chunks[i]["section"], "text": store.chunks[i]["text"][:1500]} for i in ids]
    if name == "key_accounts":
        rows = run_tool("key_accounts", {"corp": args.get("corp"), "year": 2025}).get("rows", [])
        return [r for r in rows if r["fs_nm"].startswith("연결")]
    hits = web_search(args.get("query", ""))[:3]
    return [
        {"title": h["title"], "date": h["date"][:16], "text": (fetch_page(h["url"]) or h["snippet"])[:1500]}
        for h in hits
    ]


def run(question, store, max_turns=10):
    t0, cost, calls = time.time(), 0.0, []
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    for _ in range(max_turns):
        body = {
            "model": MODEL,
            "messages": msgs,
            "tools": TOOLS,
            "max_tokens": 6000,
            "usage": {"include": True},
        }
        req = urllib.request.Request(
            os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions",
            data=json.dumps(body).encode(),
            headers={
                "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                "Content-Type": "application/json",
            },
        )
        r = json.load(urllib.request.urlopen(req, timeout=300))
        cost += float(r.get("usage", {}).get("cost") or 0)
        m = r["choices"][0]["message"]
        if m.get("tool_calls"):
            m["tool_calls"] = m["tool_calls"][:1]  # 5편 하네스: 한 턴에 도구 하나
        msgs.append({k: v for k, v in m.items() if k in ("role", "content", "tool_calls")})
        if not m.get("tool_calls"):
            return {
                "answer": (m.get("content") or "").strip(),
                "cost": round(cost, 4),
                "seconds": round(time.time() - t0, 1),
                "calls": calls,
            }
        tc = m["tool_calls"][0]
        args = json.loads(tc["function"]["arguments"] or "{}")
        s = time.time() - t0
        try:
            out = call(tc["function"]["name"], args, store)
        except Exception as e:  # noqa: BLE001 — 도구 오류도 모델에게 보여 준다
            out = {"error": str(e)[:200]}
        calls.append(
            {
                "who": tc["function"]["name"],
                "corp": args.get("corp"),
                "query": args.get("query", ""),
                "start": round(s, 1),
                "end": round(time.time() - t0, 1),
            }
        )
        msgs.append(
            {"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(out, ensure_ascii=False)[:6000]}
        )
    return {
        "answer": "(턴 상한 도달)",
        "cost": round(cost, 4),
        "seconds": round(time.time() - t0, 1),
        "calls": calls,
    }
