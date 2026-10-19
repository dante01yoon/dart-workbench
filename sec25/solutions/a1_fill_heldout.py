"""과제 1 풀이: held-out에 서술 유형이 없다(은행의 서술 문항은 13 · 24편에서 이미 돌렸다) → 사업보고서 문단에서
서술 질문 2개를 새로 만들고, 정답 낱말을 그 문단에서 고른다. 개발 문항과 같은 질문이 아닌지(twin) 확인하고 넣는다. API 호출 없음.
사용: uv run python sec25/solutions/a1_fill_heldout.py → eval/questions_v2_a1.jsonl
"""

import importlib.util
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
spec = importlib.util.spec_from_file_location("build", HERE / "03_build_set.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
CHUNKS = [json.loads(line) for line in (ROOT / "data" / "rag" / "chunks.jsonl").open()]

NEW = [  # (질문, 회사, 문단 이름에 들어갈 말, 정답 낱말 묶음)
    ("현대자동차 차량부문의 주요 원재료와 매입처는?", "현대자동차", "원재료", [["모듈"], ["현대모비스"]]),
    ("카카오는 이자율변동위험이 주로 어디서 생긴다고 설명하나?", "카카오", "위험관리", [["변동금리"]]),
]
v2 = [json.loads(line) for line in (ROOT / "eval" / "questions_v2.jsonl").open()]
dev = [r for r in v2 if r["split"] == "dev"]
print("held-out 유형(전):", dict(Counter(r["type"] for r in v2 if r["split"] == "heldout")))
for k, (q, corp, sec, keys) in enumerate(NEW, 1):
    src = [c for c in CHUNKS if c["corp"] == corp and c["year"] == 2025 and sec in c["section"]]
    ok = any(all(any(w in c["text"] for w in g) for g in keys) for c in src)  # 정답 낱말이 실제 문단에 있나
    cand = {
        "id": f"a{k}",
        "q": q,
        "type": "narrative",
        "source": "사업보고서 문단(새 문항)",
        "split": "heldout",
        "keys": keys,
    }
    clash = [d["id"] for d in dev if b.twin(cand, d)]
    print(f"  {q} · 문단 {len(src)}개 · 정답 낱말 확인 {ok} · 개발과 같은 질문 {clash or '없음'}")
    if ok and not clash:
        v2.append(cand)
print(
    "held-out 유형(후):",
    dict(Counter(r["type"] for r in v2 if r["split"] == "heldout")),
    f"· 전체 {len(v2)}문항",
)
with (ROOT / "eval" / "questions_v2_a1.jsonl").open("w", encoding="utf-8") as f:
    for r in v2:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
