"""9편 ① 조각마다 맥락 문장 만들기. 중단해도 이어서 돈다(data/rag/context.jsonl에 쌓는다).
사용: uv run python sec09/01_context.py --demo 3   → 조각 3개만 만들어 보여 준다
      uv run python sec09/01_context.py           → 전부(3,948개, 동시 16개, 40분 안팎) + data/rag/context_stats.json"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from context import DIR, OUT, load_context, make_context, sections_of
from search import load_store

chunks, _ = load_store()
secs = sections_of(chunks)
if "--demo" in sys.argv:
    n = int(sys.argv[sys.argv.index("--demo") + 1])
    picks = [
        c for c in chunks if c["corp"] == "현대자동차" and " | " in c["text"] and "매출" in c["section"]
    ][:n]
    for c in picks:
        text, u = make_context(c, secs[(c["corp"], c["section"])])
        print(
            f"■ {c['corp']} · {c['section'][-30:]}\n  조각 첫 줄: {c['text'].splitlines()[0][:60]}\n  맥락 문장: {text}\n"
        )
    sys.exit()

done = load_context()
todo = [c for c in chunks if c["id"] not in done]
print(f"남은 조각 {len(todo):,} / {len(chunks):,}", flush=True)
if not todo:  # 이미 다 만들었으면 그때 기록(조각 수 · 토큰 · 비용 · 시간)을 보여 준다
    st = json.loads((DIR / "context_stats.json").read_text())
    print(
        f"이미 완료: 조각 {st['chunks']:,}개 · 입력 {st['in']:,} · 출력 {st['out']:,}토큰 · ${st['cost']:.3f} · {st['minutes']}분"
    )
    sys.exit()
t0, tok_in, tok_out, cost = time.time(), 0, 0, 0.0
with OUT.open("a", encoding="utf-8") as f, ThreadPoolExecutor(16) as ex:
    for n, (c, (text, u)) in enumerate(
        zip(todo, ex.map(lambda c: make_context(c, secs[(c["corp"], c["section"])]), todo)), 1
    ):
        f.write(json.dumps({"id": c["id"], "context": text}, ensure_ascii=False) + "\n")
        tok_in += u.get("prompt_tokens", 0)
        tok_out += u.get("completion_tokens", 0)
        cost += float(u.get("cost") or 0)
        if n % 500 == 0:
            f.flush()
            print(f"  {n:,}/{len(todo):,}  ${cost:.3f}", flush=True)
stats = {
    "chunks": len(todo),
    "in": tok_in,
    "out": tok_out,
    "cost": round(cost, 4),
    "minutes": round((time.time() - t0) / 60, 1),
}
(DIR / "context_stats.json").write_text(json.dumps(stats))
print(
    f"완료: 조각 {len(todo):,}개 · 입력 {tok_in:,} · 출력 {tok_out:,}토큰 · ${cost:.3f} · {stats['minutes']}분"
)
