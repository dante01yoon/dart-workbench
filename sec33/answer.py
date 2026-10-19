"""33편: 최종 답 만들기 — 워크벤치 결과(보고서 문장 + 근거 카드 요약) → 화면 · API로 나가는 답 글.
22편부터 채점한 바로 그 글이다. 이 함수가 바뀌면 모델을 다시 부르지 않아도 답이 바뀐다 → CI 관문이 잡을 수 있다.
"""


def final_answer(report, evidence):
    """report: 보고서 문장 목록, evidence: 근거 카드 요약 목록 → 답 글 하나."""
    return " ".join(report) + " " + " ".join(evidence)
