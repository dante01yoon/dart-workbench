"""검색 → 인용 답변 → 검증 (강의 10편).

- 모델은 JSON으로 답한다: {"answer": [{"sentence", "cites": [청크 번호...]}], "refused": bool, "reason"}
- 인용 검증: 문장 속 숫자가 인용한 청크 본문에 실제로 있는지 문자열로 대조한다(결정적, LLM 없음).
- 투자 권유(사라/팔라/목표가/전망)는 검색 전에 거절한다.
"""

import json
import os
import re
import time
import urllib.request

from . import harness
from .search import Searcher

SYSTEM = """너는 한국 상장사 사업보고서만 근거로 답하는 리서치 도우미다.
규칙:
1. 아래 [자료]에 있는 내용만 쓴다. 자료에 없으면 refused=true, reason="공시에 없음".
2. 문장마다 근거 자료 번호를 cites에 넣는다.
3. 숫자는 자료에 적힌 그대로 단위와 함께 옮긴다. 계산했다면 계산식을 문장에 쓴다.
4. 매수·매도·목표가·주가 전망 같은 투자 권유는 하지 않는다.
JSON만 출력: {"answer":[{"sentence":"...","cites":[1]}],"refused":false,"reason":""}"""

ADVICE = re.compile(r"(사도|살까|팔까|매수|매도|투자해야|목표\s*주가|주가.*오를|주가.*내릴|사야|팔아야)")


def chat(messages, max_tokens=3000, model=None, json_mode=True):  # 추론 모델은 생각에 토큰을 먼저 써서 넉넉히
    body = {"model": model or os.environ["MODEL"], "messages": messages, "max_tokens": max_tokens}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    body["usage"] = {"include": True}  # OpenRouter: 응답에 실제 비용(usage.cost)을 넣어 준다
    if model and model == os.environ.get("FAST_MODEL"):
        body["reasoning"] = {"effort": "none"}  # 짧은 작업(재정렬·맥락 문장)은 생각 토큰 없이
    req = urllib.request.Request(os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                                          "Content-Type": "application/json"})
    t0 = time.time()
    r = json.load(urllib.request.urlopen(req, timeout=180))
    harness.record(body["model"], r.get("usage", {}), time.time() - t0)
    return r["choices"][0]["message"]["content"], r.get("usage", {})


def numbers(s):
    return re.findall(r"\d[\d,]*\.?\d*", s)


def verify(answer, ctx):
    """문장마다 숫자가 인용 청크에 있는지. 계산 결과(%, 증감)는 '계산'으로 표시하고 따로 센다."""
    out = []
    for a in answer:
        # 모델이 cites를 "1"처럼 문자열로 줄 때가 있다 → 정수로 정리
        a = {**a, "cites": [int(c) for c in a.get("cites", []) if str(c).strip().isdigit()]}
        cited = " ".join(ctx[i - 1]["text"] for i in a.get("cites", []) if 0 < i <= len(ctx))
        nums = [n for n in numbers(a["sentence"]) if len(n.replace(",", "")) >= 3 and not re.fullmatch(r"(19|20)\d\d", n)]  # 연도는 제외
        missing = [n for n in nums if n not in cited]
        status = "ok" if a.get("cites") and not missing else ("no_cite" if not a.get("cites") else "unverified")
        out.append({**a, "check": status, "missing": missing})
    return out


def ask(searcher: Searcher, q, corp=None, year=None, k=6, method="hybrid"):
    if ADVICE.search(q):
        return {"q": q, "refused": True, "reason": "투자 권유는 하지 않습니다. 공시 내용 질문으로 바꿔 주세요.", "answer": [], "ctx": []}
    f = {k_: v for k_, v in {"corp": corp, "year": year}.items() if v}
    ids = getattr(searcher, method)(q, k=k, **f)
    ctx = [searcher.chunks[i] for i in ids]
    blob = "\n\n".join(f"[{n + 1}] {c['corp']} {c['year']} · {c['section']}\n{c['text']}" for n, c in enumerate(ctx))
    for _ in range(2):  # 빈 응답·형식 오류는 한 번 더 시도(추론 모델이 가끔 빈 content를 낸다)
        raw, usage = chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": f"[자료]\n{blob}\n\n질문: {q}"}],
                           max_tokens=8000)  # 자료가 길면 추론 토큰이 3000을 다 써서 JSON이 잘렸다(응답 형식 오류 4건)
        try:
            j = json.loads(raw or "")
        except json.JSONDecodeError:
            j = {"answer": [], "refused": True, "reason": "응답 형식 오류"}
        if isinstance(j.get("answer"), list) and (j["answer"] or j.get("refused")):
            break
    return {"q": q, "refused": bool(j.get("refused")), "reason": j.get("reason", ""),
            "answer": verify(j.get("answer", []), ctx), "ctx": [c["id"] for c in ctx], "usage": usage}
