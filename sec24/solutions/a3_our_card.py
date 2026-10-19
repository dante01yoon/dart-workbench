"""과제 3 풀이: 우리 평가 세트를 공개 벤치마크처럼 한 줄 카드로 설명한다(무엇을 · 어떻게 채점 · 규모 · 대표 숫자 · 한계).
숫자는 24편 실행 기록에서 읽는다. 비교표 화면에 6번째 줄로 붙여 띄운다. API 호출 없음.
사용: uv run python sec24/solutions/a3_our_card.py → http://127.0.0.1:8828
"""

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
d = json.loads((HERE.parent / "data" / "heldout24.json").read_text())
spec = importlib.util.spec_from_file_location("bench", HERE / "01_benchmarks.py")
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)
ok = lambda rows: sum(x["correct"] for x in rows)
card = {
    "name": "DART 리서치 평가(우리)",
    "year": "2026",
    "measures": "사업보고서 기반 리서치 답의 정답 · 거절",
    "grading": "정답 낱말이 답이나 근거에 모두 있으면 정답 · 근거 없음 · 투자 권유는 거절해야 정답(코드 채점)",
    "size": "개발 20 + 처음 보는 20 · 회사 4개 · 2024~2025",
    "headline": f"개발 {ok(d['dev'])}/20 · 처음 보는 {ok(d['new'])}/20 · 문항당 ${sum(x['cost'] for x in d['dev'] + d['new']) / 40:.4f}",
    "limit": "문항 40개 · 낱말 채점이라 느슨한 키가 있다(28편) · 판사 검증 전(30편)",
    "url": "sec24/02_heldout_check.py",
    "where": "data/heldout24.json",
}
print(json.dumps(card, ensure_ascii=False, indent=1))
bench.B["rows"].append(card)
bench.serve(bench.html(), 8828)
