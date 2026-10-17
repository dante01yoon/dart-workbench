"""13편 ① 인용 검증기 시험: 팀 보고서 하나를 근거 단위(원문 일치 · 숫자 일치)와 문장 단위(심판)로 확인한다.
사용: uv run --group frameworks python sec13/01_badges.py ["질문"]"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec12"))  # 12편 팀 → sec10 → sec07
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec10"))
from team import Team
from verify import badge_sentences, numbers_ok

q = " ".join(sys.argv[1:]) or "삼성전자와 SK하이닉스의 2025년 실적과 위험 요인을 비교해 줘"
r = Team().run(q)
print(f"질문: {q}\n\n근거 {len(r['evidence'])}개")
for e in r["evidence"]:
    marks = f"원문 {'○' if e['verified'] else '×'} 숫자 {'○' if numbers_ok(e['claim'], e['quote']) else '×'}"
    print(f"  {e['id']:3s} [{marks}] {e['kind']} · {e['claim'][:58]}")
rows = badge_sentences(r["report"], r["evidence"])
print("\n보고서 문장 (심판 판정)")
for s in rows:
    print(f"  [{s['badge']}] {s['sentence']} {s['cites']}")
    if s["badge"] == "부족":
        print(f"         ↳ {s['reason']}")
cost = r["cost"] + sum(s["cost"] for s in rows)
print(
    f"\n지지 {sum(s['badge'] == '지지' for s in rows)}/{len(rows)}문장 · 팀 ${r['cost']:.4f} + 심판 ${cost - r['cost']:.4f}"
)
