"""평가 세트 초안 생성 + 정답 존재 검증. 사람(단테) 검수 전 초안이다.
숫자 문항의 정답은 재무 API(XBRL) 값에서 가져오고, 본문에서 같은 숫자가 있는 청크를 정답 청크로 삼는다.
사용: python eval/make_questions.py  → eval/questions.jsonl"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
C = [json.loads(l) for l in (ROOT / "data/chunks.jsonl").open(encoding="utf-8")]
META = json.loads((ROOT / "data/reports.json").read_text())
UNIT = {"카카오": 1}  # 카카오는 원 단위, 나머지는 백만원
NAME = {"ifrs-full_Revenue": "매출액", "dart_OperatingIncomeLoss": "영업이익", "ifrs-full_ProfitLoss": "당기순이익"}


def fin(corp, year, acc):
    m = next(x for x in META if x["corp"] == corp and x["year"] == year)
    rows = json.loads((ROOT / f"data/raw/fin_{m['corp_code']}_{year}_CFS.json").read_text())
    r = next(x for x in rows if x["sj_div"] in ("IS", "CIS") and x["account_id"] == acc)
    return int(r["thstrm_amount"])


def num(corp, year, acc):
    v = fin(corp, year, acc)
    return f"{v // UNIT.get(corp, 1_000_000):,}"


def forms(corp, year, acc):
    """같은 숫자의 표기들: 표(백만원·원) + 본문 서술("333조 6,059억원", 반올림·버림 둘 다)."""
    v = fin(corp, year, acc)
    out = {num(corp, year, acc)}
    for eok in {v // 10**8, round(v / 10**8)}:
        jo, r = divmod(eok, 10**4)
        out.add(f"{jo}조 {r:,}억" if jo else f"{r:,}억")
    return sorted(out)


Q = []


def add(type_, q, corp=None, year=None, section=None, contains=None, answer=None):
    g = {"section": section, "contains": contains} if contains else None
    Q.append({"id": f"q{len(Q) + 1:02d}", "type": type_, "q": q, "corp": corp, "year": year, "gold": g, "answer": answer})


# 숫자 (12): 재무 API 값 = 정답
for corp, year, acc in [("삼성전자", 2025, "dart_OperatingIncomeLoss"), ("삼성전자", 2024, "ifrs-full_Revenue"),
                        ("SK하이닉스", 2025, "dart_OperatingIncomeLoss"), ("SK하이닉스", 2025, "ifrs-full_ProfitLoss"),
                        ("SK하이닉스", 2024, "ifrs-full_Revenue"), ("현대자동차", 2025, "ifrs-full_Revenue"),
                        ("현대자동차", 2025, "dart_OperatingIncomeLoss"), ("현대자동차", 2024, "dart_OperatingIncomeLoss"),
                        ("카카오", 2025, "dart_OperatingIncomeLoss"), ("카카오", 2025, "ifrs-full_Revenue"),
                        ("삼성전자", 2025, "ifrs-full_ProfitLoss"), ("카카오", 2024, "dart_OperatingIncomeLoss")]:
    word = "영업수익(매출)" if corp == "카카오" and acc == "ifrs-full_Revenue" else NAME[acc]
    add("number", f"{corp}의 {year}년 연결 {word}은 얼마인가?", corp, year, None, forms(corp, year, acc),
        answer=f"{fin(corp, year, acc):,}원 (재무 API)")

# 단순 사실 (15)
facts = [
    ("삼성전자", 2025, "삼성전자의 종속기업은 몇 개인가?", None, ["308개", "| 308"]),
    ("삼성전자", 2025, "삼성전자 DS 부문이 생산하는 주요 제품은?", "사업의 개요", ["DRAM, NAND Flash"]),
    ("SK하이닉스", 2025, "SK하이닉스 본사는 어디에 있나?", None, ["경기도 이천시"]),
    ("SK하이닉스", 2025, "SK하이닉스의 주력 제품은?", "사업의 개요", ["DRAM 및 NAND"]),
    ("현대자동차", 2025, "현대자동차의 최대주주와 지분율은?", None, ["현대모비스"]),
    ("현대자동차", 2025, "현대자동차 사업부문별 매출 비중은?", "사업의 내용", ["차량부문이 약 78%"]),
    ("카카오", 2025, "카카오의 연결 사업부문은 어떻게 나뉘나?", None, ["플랫폼 부문과 콘텐츠 부문"]),
    ("카카오", 2025, "카카오 콘텐츠 부문의 하위 구성은?", "사업의 개요", ["게임, 뮤직, 스토리, 미디어"]),
    ("삼성전자", 2025, "삼성전자 보통주 주당 현금배당금은?", "배당", ["1,668"]),
    ("SK하이닉스", 2025, "SK하이닉스 보통주 주당 현금배당금은?", "배당", ["3,000"]),
    ("현대자동차", 2025, "현대자동차 보통주 주당 현금배당금은?", "배당", ["10,000"]),
    ("카카오", 2025, "카카오 보통주 주당 현금배당금은?", "배당", ["75 | 68"]),
    ("삼성전자", 2025, "삼성전자 연구개발비용은 얼마인가?", None, ["37,740,392"]),
    ("현대자동차", 2025, "현대자동차의 매출액 대비 연구개발비 비율은?", "연구개발", ["3.0%"]),
    ("카카오", 2025, "카카오 발행주식 총수는?", None, ["442,495,220"]),
]
for corp, year, q, sec, cont in facts:
    add("fact", q, corp, year, sec, cont)

# 연도 비교 (8): 두 해 숫자가 모두 있는 청크(당기·전기 열)
for corp, acc in [("삼성전자", "dart_OperatingIncomeLoss"), ("SK하이닉스", "ifrs-full_Revenue"), ("현대자동차", "ifrs-full_ProfitLoss"),
                  ("카카오", "dart_OperatingIncomeLoss")]:
    a, b = num(corp, 2025, acc), num(corp, 2024, acc)
    add("year_compare", f"{corp}의 {NAME[acc]}은 2024년 대비 2025년에 얼마나 변했나?", corp, 2025, None, forms(corp, 2025, acc),
        answer=f"2025 {a} / 2024 {b} (단위 {'원' if corp in UNIT else '백만원'})")
add("year_compare", "삼성전자 연구개발비 비율은 전년보다 늘었나 줄었나?", "삼성전자", 2025, "연구개발", ["11.3%"])
add("year_compare", "SK하이닉스 주당 배당금은 전년 대비 어떻게 바뀌었나?", "SK하이닉스", 2025, "배당", ["3,000 | 2,204"])
add("year_compare", "현대자동차 주당 배당금은 전년 대비 어떻게 바뀌었나?", "현대자동차", 2025, "배당", ["10,000 | 12,000"])
add("year_compare", "카카오 연구개발비용은 전년 대비 늘었나?", "카카오", 2025, "연구개발", ["1,299,166 | 1,269,613"])

# 회사 간 비교 (8): 회사마다 정답 청크가 따로 있다(gold_multi). 9편 "질의 분해" 실습용 — 상위 10개 안에 모든 회사의 근거가 들어오는지 본다.
ALL4 = ["삼성전자", "SK하이닉스", "현대자동차", "카카오"]
OP, REV = "dart_OperatingIncomeLoss", "ifrs-full_Revenue"
cross = [
    ("삼성전자와 SK하이닉스 중 2025년 영업이익이 더 큰 곳은?", {c: (None, forms(c, 2025, OP)) for c in ["삼성전자", "SK하이닉스"]}),
    ("2025년 매출액이 가장 큰 회사는? (삼성전자, SK하이닉스, 현대자동차, 카카오)", {c: (None, forms(c, 2025, REV)) for c in ALL4}),
    ("SK하이닉스와 삼성전자의 2025년 주당 배당금 비교", {"SK하이닉스": ("배당", ["3,000 | 2,204"]), "삼성전자": ("배당", ["1,668"])}),
    ("현대자동차와 카카오의 연구개발비 비교", {"현대자동차": ("연구개발", ["연구개발비용 계"]), "카카오": ("연구개발", ["연구개발비용 계"])}),
    ("삼성전자, SK하이닉스, 현대자동차, 카카오 중 2025년 영업이익률이 가장 높은 회사는?", {c: (None, forms(c, 2025, OP)) for c in ALL4}),
    ("삼성전자와 SK하이닉스의 환율 위험 관리 방식 차이", {"삼성전자": ("위험관리", ["환율변동"]), "SK하이닉스": ("위험관리", ["환율변동"])}),
    ("카카오와 현대자동차의 최대주주 비교", {"현대자동차": (None, ["현대모비스"]), "카카오": (None, ["김범수"])}),
    ("삼성전자와 SK하이닉스의 주요 원재료 비교", {"삼성전자": ("원재료", ["Qualcomm"]), "SK하이닉스": ("원재료", ["주요 원재료"])}),
]
for q, gm in cross:
    add("cross_company", q, None, 2025)
    Q[-1]["gold_multi"] = {c: {"section": sec, "contains": cont} for c, (sec, cont) in gm.items()}

# 위험·서술 (7)
for corp, q, sec, cont in [("삼성전자", "삼성전자는 환율변동위험을 어떻게 관리하나?", "위험관리", ["환율변동"]),
                           ("SK하이닉스", "SK하이닉스가 노출된 환율변동위험의 주요 통화는?", "위험관리", ["달러화, 유로화, 위안화 및 엔화"]),
                           ("현대자동차", "현대자동차는 이자율·외환위험을 어떻게 회피하나?", "위험관리", ["파생상품계약"]),
                           ("카카오", "카카오가 정의하는 외환위험이란?", "위험관리", ["외환위험이란"]),
                           ("삼성전자", "삼성전자 DX 부문의 주요 원재료와 공급처는?", "원재료", ["Qualcomm"]),
                           ("카카오", "카카오 플랫폼 부문의 구성은?", "사업의 개요", ["톡비즈"]),
                           ("현대자동차", "현대자동차 금융부문은 어떤 사업을 하나?", "사업의 내용", ["할부금융"])]:
    add("narrative", q, corp, 2025, sec, cont)

# 답 없음 (5) / 투자 권유 거절 (5): 검색 성적에서 제외, 답변 단계에서 채점
for q, c in [("삼성전자의 2027년 매출 전망치는?", "삼성전자"), ("카카오의 2026년 3분기 영업이익은?", "카카오"),
             ("SK하이닉스 대표이사의 연봉 협상 결과는?", "SK하이닉스"), ("현대자동차 다음 신차 출시일은?", "현대자동차"),
             ("LG전자의 2025년 영업이익은?", None)]:
    add("none", q, c, None)
for q in ["삼성전자 주식 지금 사도 될까?", "SK하이닉스와 삼성전자 중 어디에 투자해야 해?", "카카오 주가 내년에 오를까?",
          "현대차 목표 주가 알려줘", "배당 많이 주는 이 4개 중에 뭘 살까?"]:
    add("refuse", q)

# 정답 청크는 '정답 문자열이 들어 있는 모든 청크'(섹션 지정은 숫자가 흔해서 헷갈릴 때만)
# 검증: 정답 청크가 실제로 있는지
bad = 0
for q in Q:
    for corp, gm in q.get("gold_multi", {}).items():
        if not any(c["corp"] == corp and c["year"] == q["year"] and (not gm["section"] or gm["section"] in c["section"])
                   and any(x in c["text"] for x in gm["contains"]) for c in C):
            bad += 1
            print("정답 청크 없음:", q["id"], corp, gm)
    g = q["gold"]
    if not g:
        continue
    n = sum(1 for c in C if c["corp"] == q["corp"] and c["year"] == q["year"]
            and (not g["section"] or g["section"] in c["section"]) and any(s in c["text"] for s in g["contains"]))
    q["gold_chunks"] = n
    if n == 0:
        bad += 1
        print("정답 청크 없음:", q["id"], q["q"], g)
(ROOT / "eval/questions.jsonl").write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in Q))
from collections import Counter
print(len(Q), "문항", dict(Counter(q["type"] for q in Q)), "정답 없음", bad)
sys.exit(1 if bad else 0)
