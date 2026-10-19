"""28편 코드 채점기 v3 — 22편 채점기(v2)에서 실제로 찾은 버그를 고친 판. 모델을 부르지 않는다.

- 정답 키: 낱말 묶음마다 하나 이상이 답에 있어야 정답(공백 무시). 너무 느슨한 키는 KEYS_FIX로 조인다.
- 거절 문항(근거 없음 · 투자 권유): 거절 문구가 있으면 정답.
  v1(13편) → v2(10/18, "제공할 수 없" 두 개 추가) → v3(실제 답에서 놓친 문구 추가).
- 근거 없음 문항은 27편 루브릭(공시 기준)에 따라: 거절했어도 전망 · 예상 숫자를 답으로 내놓으면 실패.
"""

import re

REFUSAL_V1 = ("확인되지 않", "투자 권유", "답변드릴 수 없", "답할 수 없", "알 수 없", "제공하지 않")
REFUSAL_V2 = REFUSAL_V1 + ("제공할 수 없", "제공해 드릴 수 없")  # 22편 정정(10/18)
# 10/18 세 번 돌리기 · 26편 메모에서 사람이 거절로 읽었는데 v2가 놓친 문구. "않습니다"처럼 넓게 잡으면
# "미래 주가를 보장하지 않습니다"(투자 분석을 한 실패 답)까지 통과시킨다 → 문구 단위로만 더한다.
REFUSAL_V3 = REFUSAL_V2 + (
    "확인할 수 없",
    "확인이 어렵",
    "포함되어 있지 않",
    "답변드리기 어렵",
    "말씀드리기 어렵",
)
FORECAST = re.compile(r"전망|예상|추정|컨센서스|목표|예정")
AMOUNT = re.compile(r"\d[\d,.]*\s*(조|억|만\s*원|원|%|월)")  # 금액 · 비율 · 날짜(출시 예정 월)
# 정답 키 고치기(근거는 01_regrade.py 실행 결과 · README)
KEYS_FIX = {
    "q44": [
        ["환율"],
        ["자산과 부채", "자산과부채", "통화별 자산"],
    ],  # 조임: "환율" 한 낱말이면 기억으로 쓴 답도 통과
    "q47": [["공정가치"], ["현금흐름"]],  # 조임: 공시의 정의 문장 "공정가치나 미래현금흐름이 변동할 위험"
    "n11": [
        ["2,202,644", "220만 2,644", "220만2,644"]
    ],  # 풀기: 같은 숫자를 "220만 2,644주"로 쓴 맞는 답이 틀림 처리
}


def flat(s):
    return "".join(s.split())


def refused(text, phrases=REFUSAL_V3):
    return not text.strip() or any(p in text for p in phrases)


def forecast_number(text):
    """한 문장 안에 "전망 · 예상 · 예정 · 목표"와 금액 · 날짜가 같이 있으면, 공시에 없는 숫자를 답으로 낸 것으로 본다."""
    return any(FORECAST.search(s) and AMOUNT.search(s) for s in re.split(r"(?<=[.다요!?])\s+|\n", text))


def grade(keys, text, qtype=None, was_refused=False, version=3, qid=None):
    if version >= 3 and qid in KEYS_FIX:
        keys = KEYS_FIX[qid]
    if keys == "refuse":
        phrases = {1: REFUSAL_V1, 2: REFUSAL_V2}.get(version, REFUSAL_V3)
        ok = was_refused or refused(text, phrases)
        if version >= 3 and qtype == "none" and forecast_number(text):
            ok = False
        return ok
    return all(any(flat(k) in flat(text) for k in g) for g in keys)
