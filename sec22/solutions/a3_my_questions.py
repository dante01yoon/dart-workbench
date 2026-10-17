"""과제 3 풀이: 성적표에 내 질문 5개를 더해 처음 vs 지금을 다시 잰다.
질문마다 정답 키(이 낱말들이 모두 답이나 근거에 있어야 정답)를 직접 정한다. 숫자는 재무 API 값, 서술은 사업보고서 목차 낱말로.
거절해야 맞는 질문은 키를 "refuse"로.
사용: uv run python sec22/solutions/a3_my_questions.py → data/scorecard.jsonl에 두 줄 · data/final_eval_mine.json
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "final", Path(__file__).resolve().parent.parent / "01_final_scorecard.py"
)
final = importlib.util.module_from_spec(spec)
spec.loader.exec_module(final)

MINE = {  # 정답 키는 재무 API 값으로 직접 계산했다(2025 연결)
    "m1": (
        "SK하이닉스의 2025년 연결 당기순이익은 얼마인가?",
        "number",
        [["42조9,479억", "42,947,902", "429,479억"]],
    ),
    "m2": (
        "카카오와 현대자동차 중 2025년 영업이익률이 더 높은 곳은?",  # 카카오 9.0% vs 현대자동차 6.2%
        "cross_company",
        [["카카오"], ["9.0%", "9%", "9.04"], ["6.2%", "6.1%", "6.16"]],
    ),
    "m3": (
        "현대자동차의 2025년 연결 매출액은 전년보다 얼마나 늘었나?",
        "year_compare",
        [["186조2,545억", "186,254"], ["175조2,311억", "175,231"]],
    ),
    "m4": ("SK하이닉스는 이자율변동위험을 어떻게 관리하나?", "narrative", [["이자율"], ["변동"]]),
    "m5": ("카카오 주가가 내년에 오를까?", "refuse", "refuse"),
}
for qid, (q, t, key) in MINE.items():
    final.qs[qid] = {"id": qid, "q": q, "type": t}
    final.ks[qid] = key
final.main(list(MINE), "내 질문 5개")
