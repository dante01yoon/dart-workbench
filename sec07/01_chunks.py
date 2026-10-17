"""7편 ① 사업보고서 4권 → 청크. 표 조각에 머리 행을 다시 붙인 예를 하나 보여 준다.
사용: uv run python sec07/01_chunks.py → data/rag/chunks.jsonl"""

import json

from rag import CORPS, DIR, build_chunks

rows = build_chunks()
DIR.mkdir(parents=True, exist_ok=True)
with (DIR / "chunks.jsonl").open("w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
for corp in CORPS:
    mine = [r for r in rows if r["corp"] == corp]
    print(f"{corp:6s} 청크 {len(mine):5,}개 · 평균 {sum(len(r['text']) for r in mine) // len(mine)}자")
print(f"합계 {len(rows):,}개 → data/rag/chunks.jsonl\n")
prev = {}
for r in rows:  # 표가 잘린 뒤의 조각: 앞 조각과 첫 줄(캡션·머리 행)이 같다
    p = prev.get((r["corp"], r["section"]))
    if (
        r["corp"] == "현대자동차"
        and "매출" in r["section"]
        and p
        and r["text"].split("\n")[0] == p.split("\n")[0]
    ):
        print(f"표가 잘린 뒤 조각 · {r['corp']} {r['year']} · {r['section']}\n{r['text'][:420]}")
        break
    prev[(r["corp"], r["section"])] = r["text"]
