"""Contextual Retrieval (Anthropic, 2024) 재현: 청크마다 "이 조각이 문서 어디의 무엇인지" 1~2문장을 LLM으로 만들어 앞에 붙인다.
원 논문은 문서 전체를 넣지만 사업보고서는 수백만 자라서, 같은 섹션 본문(앞 6,000자)을 문서 대신 넣는다.
결과는 data/context.jsonl에 청크 id별로 쌓는다(중단해도 이어서 실행).
사용: python -m dart_rag.contextualize [동시 요청 수=8]"""

import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from . import dart
from .answer import chat
from .search import load_chunks

OUT = dart.ROOT / "data" / "context.jsonl"
PROMPT = """<section>
{section_text}
</section>
위는 {corp} {year}년 사업보고서의 「{section}」 섹션이다. 아래 조각이 이 섹션에서 무엇에 관한 내용인지,
검색에 도움이 되도록 한국어 1~2문장으로만 써라(회사·연도·표 이름·지표 이름을 넣고, 숫자는 다시 쓰지 마라).
<chunk>
{chunk}
</chunk>"""


def main(workers=8):
    chunks = load_chunks()
    done = {json.loads(l)["id"] for l in OUT.open(encoding="utf-8")} if OUT.exists() else set()
    by_sec = defaultdict(list)
    for c in chunks:
        by_sec[(c["rcept_no"], c["section"])].append(c["text"])
    todo = [c for c in chunks if c["id"] not in done]
    print(f"남은 청크 {len(todo)} / {len(chunks)}", flush=True)

    def one(c):
        sec = "\n".join(by_sec[(c["rcept_no"], c["section"])])[:6000]
        msg = PROMPT.format(section_text=sec, corp=c["corp"], year=c["year"], section=c["section"], chunk=c["text"][:2000])
        err = "빈 응답"
        for _ in range(3):
            try:
                txt, u = chat([{"role": "user", "content": msg}], max_tokens=250, model=os.environ["FAST_MODEL"], json_mode=False)
                if txt:
                    return {"id": c["id"], "context": txt.strip(), "in": u.get("prompt_tokens", 0), "out": u.get("completion_tokens", 0)}
            except Exception as e:  # noqa: BLE001 — 네트워크 오류는 재시도
                err = e
        return {"id": c["id"], "context": "", "error": str(err)[:200]}

    with OUT.open("a", encoding="utf-8") as f, ThreadPoolExecutor(workers) as ex:
        for n, r in enumerate(ex.map(one, todo), 1):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            if n % 500 == 0:
                f.flush()
                print(f"  {n}/{len(todo)}", flush=True)
    print("완료", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
