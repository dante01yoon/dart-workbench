"""과제 2 풀이: held-out 잠그기 — (1) 실행 기록(data/*.json · *.jsonl)에 held-out 질문이 이미 나온 적 있는지(= 누가 돌려 봤는지) 찾아
나왔으면 개발로 옮기고, (2) 남은 held-out의 지문(sha256)을 남겨 누가 고치면 알 수 있게 한다. API 호출 없음.
사용: uv run python sec25/solutions/a2_lock.py → eval/questions_v2_locked.jsonl · eval/heldout_v2.sha256
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
v2 = [json.loads(line) for line in (ROOT / "eval" / "questions_v2.jsonl").open()]
logs = [
    p for p in (ROOT / "data").glob("*.json*") if not p.name.startswith("sec25_")
]  # 25편이 만든 후보 · 정답 파일은 제외
held = [r for r in v2 if r["split"] == "heldout"]
for r in held:
    seen = [p.name for p in logs if r["q"] in p.read_text(encoding="utf-8")]
    if seen:
        r["split"] = "dev"
        print(f"이미 돌린 문항: {r['id']} {r['q']} ({', '.join(seen)}) → 개발로")
held = [r for r in v2 if r["split"] == "heldout"]
blob = json.dumps([[r["id"], r["q"], r["keys"]] for r in held], ensure_ascii=False, sort_keys=True).encode()
digest = hashlib.sha256(blob).hexdigest()
lock = ROOT / "eval" / "heldout_v2.sha256"
if lock.exists() and lock.read_text().strip() != digest:
    print("경고: 잠근 뒤에 held-out이 바뀌었다")
lock.write_text(digest + "\n")
with (ROOT / "eval" / "questions_v2_locked.jsonl").open("w", encoding="utf-8") as f:
    for r in v2:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"실행 기록 {len(logs)}개 확인 · held-out {len(held)}문항 지문 {digest[:16]}… → {lock.name}")
