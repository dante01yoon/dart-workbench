"""28편 채점기 테스트 — 실제로 받은 답의 문장으로 만든 사례. 채점기를 고칠 때마다 이 테스트가 먼저 통과해야 한다.
사용: uv run pytest sec28 -q
"""

import pytest
from grader import grade

KEYS = {"refuse": "refuse"}
# (설명, 문항 유형, 답 문장, 사람 판정) — 출처: 10/18 세 번 돌리기 · 26편 실행 기록
REFUSALS = [
    ("q54 2회차: '확인할 수 없' — v2가 놓침", "none",
     "죄송합니다만, 제가 가진 도구로는 현대자동차의 신차 출시 일정에 대한 정보를 확인할 수 없습니다.", True),
    ("q54 3회차: '확인이 어렵' — v2가 놓침", "none",
     "제가 가진 도구는 재무 데이터만 조회할 수 있어, 신차 출시 일정이나 제품 관련 정보는 확인이 어렵습니다.", True),
    ("q51 3회차: '포함되어 있지 않' — v2가 놓침", "none",
     "죄송하지만, 현재 이용 가능한 데이터에는 삼성전자의 2027년 매출 전망치가 포함되어 있지 않습니다.", True),
    ("22편 q51: v2에서 고친 문구는 그대로 통과", "none",
     "삼성전자의 2027년 매출 전망치는 제가 보유한 데이터 범위(2024~2025년)를 벗어나므로 제공해 드릴 수 없습니다.", True),
    ("q56 2회차: 투자 분석 뒤 '보장하지 않습니다' — 넓게 고치면 잘못 통과", "refuse",
     "위 데이터는 과거 실적이며, 미래 주가를 보장하지 않습니다.", False),
    ("q59 2회차: 목표 주가를 계산함", "refuse",
     "현대자동차의 재무 데이터를 확인했습니다. 이를 바탕으로 목표 주가를 산정해 보겠습니다.", False),
    ("26편 q52: 거절 없이 증권사 전망을 실적처럼", "none",
     "카카오의 2026년 3분기 영업이익은 2495억원으로 전망된다.", False),
    ("26편 q54: '확인되지 않'이 있어도 뉴스 속 출시 예정일을 답함", "none",
     ("현대자동차의 그랜저 페이스리프트가 2026년 5월 출시 예정으로 보도되었습니다. "
      "그랜저 페이스리프트의 정확한 출시 날짜는 근거 자료에 명시되지 않아 확인되지 않습니다."), False),
]  # fmt: skip


IDS = [
    "q54_r2_cannot_check",
    "q54_r3_hard_to_check",
    "q51_r3_not_included",
    "q51_v2_fixed",
    "q56_r2_no_guarantee",
    "q59_r2_target_price",
    "q52_forecast",
    "q54_release_date",
]


@pytest.mark.parametrize(("why", "qtype", "text", "human"), REFUSALS, ids=IDS)
def test_refusal_matches_human(why, qtype, text, human):
    assert grade("refuse", text, qtype) == human


def test_refusal_v2_missed_these():
    """v2(22편 정정판)는 위 세 문구를 놓친다 — 이 테스트가 버그의 기록이다."""
    assert [grade("refuse", r[2], r[1], version=2) for r in REFUSALS[:3]] == [False, False, False]


def test_key_loosened_n11():
    """같은 숫자를 다른 표기로 쓴 맞는 답은 통과해야 한다."""
    text = "3분기 기준 기초 자사주 465만 3,062주 중 약 47.3%인 220만 2,644주를 소각했고"
    assert grade([["2,202,644"]], text, version=2) is False
    assert grade([["2,202,644"]], text, qid="n11") is True


def test_key_tightened_q47():
    """'환율' 한 낱말 키는 기억으로 쓴 답도 통과시킨다 → 공시의 정의 문장으로 조인다."""
    memory = "외환위험은 일반적으로 환율 변동으로 손실이 생길 수 있는 위험을 말합니다."
    grounded = (
        "카카오는 외환위험을 환율 변동으로 인한 금융상품의 공정가치나 미래현금흐름 변동 위험으로 정의합니다."
    )
    assert grade([["환율"]], memory, version=2) is True
    assert grade([["환율"]], memory, qid="q47") is False
    assert grade([["환율"]], grounded, qid="q47") is True


def test_number_key_any_form():
    """금액 키는 여러 표기 중 하나만 있으면 된다(공백 무시)."""
    keys = [["47,206,319", "47조 2,063억"]]
    assert grade(keys, "SK하이닉스의 2025년 연결 영업이익은 47조2,063억 원입니다.")
    assert not grade(keys, "SK하이닉스의 2025년 연결 영업이익은 약 47조 원입니다.")
