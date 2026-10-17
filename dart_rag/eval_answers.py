"""답변 성적표 (강의 1편 성적표 v0 → 매 섹션 재측정).
검색만이 아니라 질문 → 검색 → 답변 전체를 잰다. LLM 채점 없이 문자열로:
  - eval/answer_keys.json: 문항마다 [[이 중 하나], [이 중 하나], ...] — 모든 묶음이 답에 들어 있어야 통과
  - 'refuse' 문항(답 없음·투자 권유)은 거절해야 통과
  - 인용 검증: 숫자가 들어간 문장이 인용 청크에서 확인되는 비율
사용: python -m dart_rag.eval_answers [hybrid|rerank|decompose_llm] [--para] [--limit N]
"""

import json
import re
import sys
import time

from . import dart
from .answer import ask
from .harness import Trace
from .search import Searcher, build_vectors, load_chunks, load_context

KEYS = json.loads((dart.ROOT / "eval" / "answer_keys.json").read_text())


def flat(s):
    return re.sub(r"\s+", "", s)


def passed(key, r):
    if key == "refuse":
        return r["refused"]
    if r["refused"]:
        return False
    text = flat(" ".join(a["sentence"] for a in r["answer"]))
    return all(any(flat(k) in text for k in group) for group in key)


def main(method="hybrid", para=False, limit=None, use_ctx=True):
    chunks = load_chunks()
    ctx = load_context() if use_ctx else None
    s = Searcher(chunks, build_vectors(chunks, ctx), ctx)
    qs = [json.loads(l) for l in (dart.ROOT / "eval" / "questions.jsonl").open(encoding="utf-8")][:limit]
    name = f"answer · {method}{' · ctx' if use_ctx else ''}{' · 말바꿈' if para else ''}"
    by_type, checked, ok_sent, rows = {}, 0, 0, []
    with Trace(name) as tr:
        for q in qs:
            t0 = time.time()
            text = q.get("q_para") if para and q.get("q_para") else q["q"]
            r = ask(s, text, q.get("corp"), q.get("year"), method=method)
            ok = passed(KEYS[q["id"]], r)
            tr.item(q["id"], ok, time.time() - t0)
            a, b = by_type.get(q["type"], (0, 0))
            by_type[q["type"]] = (a + ok, b + 1)
            num_sents = [x for x in r["answer"] if x.get("missing") is not None and re.search(r"\d", x["sentence"])]
            checked += len(num_sents)
            ok_sent += sum(x["check"] == "ok" for x in num_sents)
            rows.append({"id": q["id"], "type": q["type"], "q": text, "ok": ok, "refused": r["refused"],
                         "answer": " ".join(x["sentence"] for x in r["answer"]) or r.get("reason", "")})
            print(f"{'✅' if ok else '❌'} {q['id']} {q['type']:13s} {text[:36]}", flush=True)
    row = tr.save(method=method, para=para, ctx=use_ctx, by_type={k: f"{a}/{b}" for k, (a, b) in by_type.items()},
                  cite_verified=round(ok_sent / checked, 3) if checked else None)
    (dart.ROOT / "eval" / f"answers-{method}{'-para' if para else ''}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print(json.dumps(row, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    if lim:
        args = [a for a in args if a != str(lim)]
    main(args[0] if args else "hybrid", "--para" in sys.argv, lim)
