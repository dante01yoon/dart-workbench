"""9편 공용: Contextual Retrieval(Anthropic, 2024) 재현.

조각마다 "이 조각이 문서 어디의 무엇인지" 1~2문장을 모델이 써서 앞에 붙인다. 숫자뿐인 표 조각도 무슨 표인지 알게 된다.
원래 방법은 문서 전체를 함께 넣지만, 사업보고서는 80만 자라서 같은 섹션 본문(앞 6,000자)을 대신 넣는다.
"""

import json
import os
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec08"))
from search import DIR, MODEL  # 8편 공용 모듈을 그대로 쓴다

PROMPT = """<section>
{section_text}
</section>
위는 {corp} {year}년 사업보고서의 「{section}」 섹션이다. 아래 조각이 이 섹션에서 무엇에 관한 내용인지,
검색에 도움이 되도록 한국어 1~2문장으로만 써라(회사·연도·표 이름·지표 이름을 넣고, 숫자는 다시 쓰지 마라).
<chunk>
{chunk}
</chunk>"""
OUT = DIR / "context.jsonl"


def chat(msg, max_tokens=4000):
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": msg}],
        "max_tokens": max_tokens,
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
    u = r.get("usage", {})
    return (r["choices"][0]["message"].get("content") or "").strip(), u


def sections_of(chunks):
    by = defaultdict(list)
    for c in chunks:
        by[(c["corp"], c["section"])].append(c["text"])
    return {k: "\n".join(v)[:6000] for k, v in by.items()}


def make_context(c, sec_text):
    msg = PROMPT.format(
        section_text=sec_text, corp=c["corp"], year=c["year"], section=c["section"], chunk=c["text"][:2000]
    )
    for _ in range(3):  # 빈 답이나 네트워크 오류는 다시 시도
        try:
            text, u = chat(msg)
            if text:
                return text, u
        except Exception:  # noqa: BLE001, S112
            continue
    return "", {}


def load_context():
    if not OUT.exists():
        return {}
    return {r["id"]: r["context"] for r in map(json.loads, OUT.open(encoding="utf-8")) if r.get("context")}
