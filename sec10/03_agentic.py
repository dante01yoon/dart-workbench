"""10편 ③ 에이전트형 RAG: 검색 한 번으로 끝내지 않고, 모델이 공시 검색 · 재무 API 도구를 골라 여러 번 부른다.
같은 11문항(전년 대비 8 · 회사 비교 3)을 RAG 한 번(01·02와 같은 답 함수)과 에이전트로 풀어 정답 · 도구 호출 · 비용을 잰다.
금액 전년 대비(q28~q31)는 두 해 금액이 모두 재무 API와 맞아야 정답, 나머지는 정답 키(answer_keys.json)로 채점한다.
사용: uv run python sec10/03_agentic.py → data/rag/agentic.json"""

import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from cite import (
    DIR,
    NO_ADVICE,
    NO_EVIDENCE,
    Store,
    answer,
    api_value,
    correct,
    keys,
    match_api,
    prior_values,
    questions,
    run_tool,
)
from search import MODEL

QIDS = ["q28", "q29", "q30", "q31", "q32", "q33", "q34", "q35", "q36", "q37", "q40"]
CORPS = ["삼성전자", "SK하이닉스", "현대자동차", "카카오"]
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_report",
            "description": "2025년 사업보고서 본문 검색(서술 · 표). 결과 조각마다 [S번호]가 붙는다.",
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
            "description": "재무 API 주요 계정(연결 · 별도): 매출액 · 영업이익 · 당기순이익 · 자산 · 부채(당기 · 전기, 원). 결과에 [API]를 붙여 인용한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "corp": {"type": "string", "enum": CORPS},
                    "year": {"type": "integer", "enum": [2024, 2025]},
                },
                "required": ["corp", "year"],
            },
        },
    },
]
SYSTEM = f"""너는 사업보고서 Q&A 에이전트다. 도구로 근거를 모은 뒤 답한다.
- 금액은 key_accounts(재무 API)를, 서술 · 비율 · 배당 · 연구개발 같은 표는 search_report를 쓴다.
- 문장마다 끝에 근거를 [S3]이나 [API]처럼 단다. 숫자는 근거에 적힌 그대로 쓰고, 계산했으면 "계산:"으로 시작한다.
- 근거를 못 찾으면 이 한 줄만: {NO_EVIDENCE}
- 투자 판단을 묻으면 이 한 줄만: {NO_ADVICE}"""


def llm(messages):
    body = {
        "model": MODEL,
        "messages": messages,
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
    m = r["choices"][0]["message"]
    if m.get("tool_calls"):  # 5편 하네스: 한 턴에 도구 하나만
        m["tool_calls"] = m["tool_calls"][:1]
    return m, float(r.get("usage", {}).get("cost") or 0)


def agent(store, q, max_turns=8):
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": q}]
    calls, cost, seen = [], 0.0, []
    for _ in range(max_turns):
        m, c = llm(msgs)
        cost += c
        msgs.append({k: v for k, v in m.items() if k in ("role", "content", "tool_calls")})
        if not m.get("tool_calls"):
            return (m.get("content") or "").strip() or "(빈 답)", calls, cost
        tc = m["tool_calls"][0]
        args = json.loads(tc["function"]["arguments"] or "{}")
        name = tc["function"]["name"]
        calls.append(f"{name}({', '.join(str(v) for v in args.values())})")
        if name == "search_report":
            hits = store.search(args.get("query", q), args.get("corp"), k=5)
            out = []
            for i in hits:
                seen.append(i)
                out.append(
                    f"[S{len(seen)}] ({store.chunks[i]['corp']} · {store.chunks[i]['section']})\n{store.chunks[i]['text'][:1500]}"
                )
            result = "\n\n".join(out)
        else:
            rows = run_tool("key_accounts", args).get("rows", [])
            result = json.dumps([r for r in rows if r["fs_nm"].startswith("연결")], ensure_ascii=False)
        msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
    return "(도구 호출 한도에서 멈춤)", calls, cost


store, qs, ks = Store(), questions(), keys()


def grade(qid, text):
    """금액 전년 대비 문항(q28~q31)은 2025 · 2024 두 해 금액이 모두 재무 API와 맞아야 정답. 나머지는 정답 키.
    2024년 금액은 2024년 보고서 값과 2025년 보고서가 다시 쓴 값(재작성) 중 하나면 맞다."""
    q = qs[qid]
    if qid in ("q28", "q29", "q30", "q31"):
        now = match_api(text, api_value(q["corp"], 2025, q["q"])[1])
        return now and any(match_api(text, v) for v in prior_values(q["corp"], q["q"]))
    return correct(text, ks[qid])


def run(qid):
    q = qs[qid]
    rag_text, _, rag_cost = answer(store, q["q"], q["corp"])
    ag_text, calls, ag_cost = agent(store, q["q"])
    return {
        "id": qid,
        "q": q["q"],
        "rag": {"answer": rag_text, "correct": grade(qid, rag_text), "cost": rag_cost},
        "agent": {"answer": ag_text, "correct": grade(qid, ag_text), "calls": calls, "cost": ag_cost},
    }


if __name__ == "__main__":
    with ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(run, QIDS))
    for r in rows:
        print(
            f"{r['id']} RAG {'✅' if r['rag']['correct'] else '❌'}  에이전트 {'✅' if r['agent']['correct'] else '❌'} "
            f"도구 {len(r['agent']['calls'])}번  {r['q'][:30]}"
        )
    for who in ("rag", "agent"):
        n = sum(r[who]["correct"] for r in rows)
        extra = (
            f" · 도구 평균 {sum(len(r['agent']['calls']) for r in rows) / len(rows):.1f}번"
            if who == "agent"
            else ""
        )
        print(
            f"{'RAG 한 번' if who == 'rag' else '에이전트':6s} 정답 {n}/{len(rows)} · ${sum(r[who]['cost'] for r in rows):.4f}{extra}"
        )
    (DIR / "agentic.json").write_text(json.dumps(rows, ensure_ascii=False))
