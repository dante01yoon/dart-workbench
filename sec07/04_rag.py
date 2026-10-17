"""7편 ④ RAG로 답하기: 4편과 같은 질문 6개를 "찾아서 5조각만 넣기"로 답하고, 정답과 토큰을 잰다.
질문 → (회사·연도 필터) 벡터 검색 상위 5개 → Flash에게 발췌만 근거로 [번호] 출처를 달아 답하게 한다.
사용: uv run python sec07/04_rag.py"""

import json
import os
import urllib.request

from rag import YEAR, load_store, search
from tools15 import ROOT

MODEL = os.environ.get("MODEL_RAG", "deepseek/deepseek-v4-flash")
QIDS = ["q25", "q26", "q32", "q35", "q18", "q20"]  # 4편과 같은 질문


def answer(q, corp, chunks, emb, k=5):
    hits = search(q, chunks, emb, k=k, corp=corp, year=YEAR)
    ctx = "\n\n".join(f"[{n + 1}] ({chunks[i]['section']})\n{chunks[i]['text']}" for n, i in enumerate(hits))
    msg = f"아래 사업보고서 발췌만 근거로 답하라. 문장 끝에 [1]처럼 출처 번호를 달고, 숫자는 원문 그대로 적어라. 발췌에 없으면 없다고 답하라.\n\n질문: {corp} {YEAR}년 {q}\n\n{ctx}"
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": msg}],
        "max_tokens": 6000,  # 처음엔 1500 → 생각(reasoning)에 다 써서 빈 답이 나왔다
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
    u, c = r.get("usage", {}), r["choices"][0]
    text = c["message"].get("content") or ""
    if not text and c.get("finish_reason") == "length":  # 빈 답을 그냥 넘기지 않는다
        text = "(답을 다 쓰지 못했습니다: 생각하는 데 토큰 한도를 모두 썼습니다)"
    return (
        text,
        hits,
        u.get("prompt_tokens", 0),
        float(u.get("cost") or 0),
    )


def flat(s):
    return "".join(s.split())


if __name__ == "__main__":
    chunks, emb = load_store()
    qs = {json.loads(line)["id"]: json.loads(line) for line in (ROOT / "eval" / "questions.jsonl").open()}
    keys = json.loads((ROOT / "eval" / "answer_keys.json").read_text())
    ok_n, tok, cost = 0, 0, 0.0
    for qid in QIDS:
        q = qs[qid]
        text, hits, t, c = answer(q["q"], q["corp"], chunks, emb)
        ok = all(any(flat(k) in flat(text) for k in g) for g in keys[qid])
        ok_n, tok, cost = ok_n + ok, tok + t, cost + c
        print(f"{'✅' if ok else '❌'} {q['q']:28s} 입력 {t:5,}토큰  출처 {chunks[hits[0]]['section'][:36]}")
    print(f"\nRAG(상위 5조각): 통과 {ok_n}/{len(QIDS)} · 입력 {tok:,}토큰 · ${cost:.4f}")
