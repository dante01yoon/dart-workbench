"""컨텍스트가 길어지면 무엇이 나빠지나 (강의 4편).

같은 질문·같은 정답 청크에, 같은 회사의 관련 없는 청크를 0 / 30 / 100개 섞어 넣는다(정답은 가운데).
지표: 정답률(answer_keys), 입력 토큰, 지연, 비용.
사용: python -m dart_rag.context_rot → data/context_rot.json
"""

import json
import random
import time
from concurrent.futures import ThreadPoolExecutor

from . import dart
from .answer import SYSTEM, chat
from .eval_answers import KEYS, passed
from .search import Searcher, build_vectors, load_chunks, load_context

PADS = [0, 30, 100]


def main():
    chunks = load_chunks()
    ctx = load_context()
    s = Searcher(chunks, build_vectors(chunks, ctx), ctx)
    qs = [json.loads(l) for l in (dart.ROOT / "eval" / "questions.jsonl").open(encoding="utf-8")]
    qs = [q for q in qs if q["type"] in ("number", "fact")][:20]
    rng = random.Random(7)

    def run(q, pad):
        ids = s.rerank(q["q"], k=6, corp=q["corp"], year=q["year"])
        pool = [i for i in s._mask(corp=q["corp"], year=q["year"]) if i not in ids]
        noise = rng.sample(pool, pad) if pad else []
        order = noise[: pad // 2] + ids + noise[pad // 2:]
        blob = "\n\n".join(f"[{n + 1}] {chunks[i]['corp']} {chunks[i]['year']} · {chunks[i]['section']}\n{chunks[i]['text']}"
                           for n, i in enumerate(order))
        t0 = time.time()
        raw, u = chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": f"[자료]\n{blob}\n\n질문: {q['q']}"}])
        try:
            j = json.loads(raw or "")
        except json.JSONDecodeError:
            j = {"answer": [], "refused": True}
        r = {"refused": bool(j.get("refused")), "answer": j.get("answer") if isinstance(j.get("answer"), list) else []}
        return {"id": q["id"], "pad": pad, "ok": passed(KEYS[q["id"]], r), "prompt_tokens": u.get("prompt_tokens", 0),
                "seconds": round(time.time() - t0, 2), "cost": float(u.get("cost") or 0)}

    out = []
    for pad in PADS:
        with ThreadPoolExecutor(6) as ex:
            rows = list(ex.map(lambda q: run(q, pad), qs))
        n = len(rows)
        res = {"pad": pad, "n": n, "accuracy": round(sum(r["ok"] for r in rows) / n, 3),
               "avg_prompt_tokens": round(sum(r["prompt_tokens"] for r in rows) / n),
               "avg_seconds": round(sum(r["seconds"] for r in rows) / n, 1),
               "cost_per_q": round(sum(r["cost"] for r in rows) / n, 5), "misses": [r["id"] for r in rows if not r["ok"]]}
        out.append(res)
        print(f"관련 없는 청크 {pad:3d}개: 정답률 {res['accuracy']:.2f}  입력 토큰 {res['avg_prompt_tokens']:6d}  "
              f"지연 {res['avg_seconds']:5.1f}s  ${res['cost_per_q']:.4f}/문항  틀림 {res['misses']}", flush=True)
    (dart.ROOT / "data" / "context_rot.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
