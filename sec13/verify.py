"""13편 공용: 인용 검증기 — {claim, source, quote}를 세 단계로 확인한다.

1. 원문 일치: quote가 원문(공시 청크 · 기사 본문 · 재무 API 줄)에 글자 그대로 있나 (LLM 없음)
2. 숫자 일치: claim에 나온 금액 · 숫자가 quote에도 있나 (LLM 없음)
3. 심판: quote가 claim을 뒷받침하나 (LLM, 예/아니오 + 이유)
보고서 문장은 인용한 근거들을 합쳐 같은 심판에게 묻는다 → 배지: 지지 · 부족 · 출처 없음
"""

import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec12"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec10"))
from team import chat, norm, parse  # 12편 팀 (sec12 → sec10 → sec07 경로도 함께 잡힌다)

JUDGE = """[주장]이 [인용]만으로 뒷받침되는지 판정하라. 인용에 없는 내용, 다른 숫자, 다른 회사 · 연도가 들어 있으면 false.
숫자는 단위만 바꾸거나 억 단위로 반올림한 것(예: 186,254,472백만원 = 186조 2,545억 원)은 같은 값으로 본다.
인용 앞 (출처: …)에 적힌 회사 · 연도도 인용의 일부로 본다(본문의 "당사"는 그 회사다).
JSON만: {"supported": true, "reason": "한 문장"}"""


def quote_ok(quote, text):
    return len(norm(quote)) >= 10 and norm(quote) in norm(text)


AMOUNT = re.compile(
    r"(\d[\d,]*)\s*조(?:\s*(\d[\d,]*)\s*억)?|(\d[\d,.]*)\s*억|(\d[\d,]*)\s*백만\s*원|(\d[\d,]{6,})\s*원?"
)


def amounts(text):
    """금액을 원 단위로: '186조 2,545억' · '7,320억' · '43,601,051백만원' · '732,036,535,379원'. 쓴 글자 범위도 돌려준다."""
    out = []
    for m in AMOUNT.finditer(text):
        jo, eok, eok2, mil, won = m.groups()
        n = lambda x: float(x.replace(",", ""))
        if jo:
            v = n(jo) * 1e12 + (n(eok) * 1e8 if eok else 0)
        elif eok2:
            v = n(eok2) * 1e8
        elif mil:
            v = n(mil) * 1e6
        else:
            v = n(won)
        out.append((v, m.span()))
    return out


def numbers_ok(claim, quote):
    """claim의 금액이 quote의 금액과 0.1% 안으로 맞고, 나머지 세 자리 이상 숫자(연도 제외)가 quote에 그대로 있나."""
    q_vals = [v for v, _ in amounts(quote)]
    used = []
    for v, span in amounts(claim):
        used.append(span)
        if not any(abs(v - w) <= max(v, w) * 0.001 for w in q_vals):
            return False
    rest = "".join(" " if any(a <= i < b for a, b in used) else ch for i, ch in enumerate(claim))
    plain = [
        n
        for n in re.findall(r"\d[\d,.]*%?", re.sub(r"\d{4}\s*년", " ", rest))
        if len(n.strip("%,.").replace(",", "")) >= 3
    ]
    return all(n.rstrip(".,") in quote for n in plain)


def judge(claim, quote):
    raw, u = chat(f"{JUDGE}\n\n[주장] {claim}\n\n[인용] {quote}", max_tokens=6000)
    if not raw:  # 생각하느라 한도를 다 쓴 경우 한 번 더
        raw, u2 = chat(f"{JUDGE}\n\n[주장] {claim}\n\n[인용] {quote}", max_tokens=18000)
        u = {"cost": float(u.get("cost") or 0) + float(u2.get("cost") or 0)}
    j = parse(raw)
    return bool(j.get("supported")), j.get("reason", "(판정 실패)"), float(u.get("cost") or 0)


def badge_sentences(report, evidence, workers=8):
    """보고서 문장마다: 인용한 근거의 quote를 합쳐 심판에게 묻는다."""
    by = {e["id"]: e for e in evidence}

    def one(s):
        quotes = [f"(출처: {by[c]['source']}) {by[c]['quote']}" for c in s.get("cites", []) if c in by]
        if not quotes:
            return {**s, "badge": "출처 없음", "reason": "", "cost": 0.0}
        ok, why, cost = judge(s["sentence"], "\n".join(quotes))
        return {**s, "badge": "지지" if ok else "부족", "reason": why, "cost": cost}

    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(one, report))
