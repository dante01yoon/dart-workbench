"""32편 ② 근거성 · 인용 — 보고서 문장마다 "출처가 있나"(코드) · "숫자가 그 출처에 있나"(코드) · "출처가 뒷받침하나"(판사).

- 재료: 26편 실행 기록의 최종 보고서 문장(인용 id 포함)과 근거. 판사 배지는 그날 워크벤치가 13편 심판으로 단 것 그대로다.
- 코드 숫자 대조는 10편 아이디어: 문장의 숫자(세 자리 이상, 연도 빼고)가 인용한 근거 원문에 있나.
  "43조 6,011억"처럼 단위를 바꿔 쓴 금액은 원 단위로 바꿔 0.1% 안이면 같다고 본다(10편 to_won).
- 코드와 판사가 서로 맞는지만 본다. 사람 판단과 맞는지는 아직 재지 않았다(사람 라벨이 없다).
모델 호출 없음. 사용: uv run python sec32/02_grounded.py → data/eval32_grounded.json
"""

import re
import sys

from agent_eval import ROOT, save, traces

sys.path.insert(0, str(ROOT / "sec10"))
from cite import to_won  # 10편: '43조 6,010억' · '7,320억원' → 원

NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
YEAR = re.compile(r"^(19|20)\d\d$")
CALC = re.compile(r"대비|증가|감소|차이|더 크|더 많|률|율|계산")


def num(t):
    return float(t.replace(",", ""))


AMOUNTS = (
    (
        re.compile(r"(\d[\d,]*)\s*조(?:\s*(\d[\d,]*)\s*억)?"),
        lambda m: [num(m[1]) * 10**12 + num(m[2] or "0") * 10**8],
    ),
    (re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*억"), lambda m: [num(m[1]) * 10**8]),
    (re.compile(r"(\d[\d,]*)\s*백만\s*원"), lambda m: [int(m.group(1).replace(",", "")) * 10**6]),
)


def numbers_ok(sentence, quotes):
    """문장의 숫자가 모두 인용 원문에 있으면 [] · 없으면 빠진 숫자 목록.
    단위를 바꿔 쓴 금액("43조 6,011억")은 원으로 바꿔 원문 금액과 0.1% 안이면 지운 뒤 나머지 숫자를 본다."""
    src, won = re.sub(r"[,\s]", "", quotes), to_won(quotes)
    for pat, value in AMOUNTS:
        for m in pat.finditer(sentence):
            if value(m) and all(any(abs(v - w) <= w * 0.001 for w in won) for v in value(m)):
                sentence = sentence.replace(m.group(0), " ")
    out = []
    for n in NUM.findall(sentence):
        d = n.replace(",", "")
        if len(d.replace(".", "")) >= 3 and not YEAR.match(d) and d not in src:
            out.append(n)
    return out


assert numbers_ok("영업이익은 43조 6,011억 원", "영업이익 당기 43,601,051,000,000원") == []
assert numbers_ok("영업이익은 43조 9,999억 원", "영업이익 당기 43,601,051,000,000원") == ["9,999"]


rows = []
for x in traces():
    ev = {e["id"]: e for e in x["evidence"]}
    for s in x["report"]:
        quotes = " ".join(ev[c]["quote"] for c in s["cites"] if c in ev)
        has_num = any(
            len(n.replace(",", "").replace(".", "")) >= 3 and not YEAR.match(n)
            for n in NUM.findall(s["sentence"])
        )
        rows.append(
            {
                "id": x["id"],
                "sentence": s["sentence"],
                "cited": bool(s["cites"]),
                "news": any("http" in ev[c]["source"] for c in s["cites"] if c in ev),
                "has_num": has_num,
                "missing": numbers_ok(s["sentence"], quotes) if s["cites"] and has_num else [],
                "judge": s["badge"],
            }
        )

n = len(rows)
cited = sum(r["cited"] for r in rows)
nums = [r for r in rows if r["has_num"] and r["cited"]]
num_ok = [r for r in nums if not r["missing"]]
sup = sum(r["judge"] == "지지" for r in rows)
answers = {r["id"] for r in rows}
all_sup = [a for a in answers if all(r["judge"] == "지지" for r in rows if r["id"] == a)]
print(f"보고서 문장 {n}개 (답 {len(answers)}개, 26편 실행 · 거절 · 빈 답은 문장 0개)")
print(f"  코드 ① 출처가 붙었나          {cited}/{n} = {cited / n * 100:.1f}%")
print(
    f"  코드 ② 숫자가 인용 원문에 있나  {len(num_ok)}/{len(nums)} = {len(num_ok) / len(nums) * 100:.1f}%  (숫자 있는 문장만)"
)
print(f"  판사 ③ 인용이 문장을 뒷받침하나 {sup}/{n} = {sup / n * 100:.1f}%  (13편 심판 · 그날 배지)")
print(f"  답 단위: 모든 문장이 '지지'인 답 {len(all_sup)}/{len(answers)}")
news = [r for r in rows if r["news"]]
print(
    f"  뉴스를 인용한 문장 {len(news)}개 — 지지 {sum(r['judge'] == '지지' for r in news)}개 (출처가 공시가 아니어도 '지지'는 나온다)"
)

print("\n코드 숫자 대조 × 판사 (숫자 있는 문장)")
both = lambda c, j: [r for r in nums if (not r["missing"]) == c and (r["judge"] == "지지") == j]
print(f"  둘 다 통과 {len(both(True, True))} · 둘 다 걸림 {len(both(False, False))}")
print(f"  코드만 걸림(판사 지지) {len(both(False, True))} · 판사만 걸림(코드 통과) {len(both(True, False))}")
calc = [r for r in both(False, True) if CALC.search(r["sentence"])]
print(
    f"    코드만 걸린 {len(both(False, True))}개 중 계산한 숫자(증감 · 비율) {len(calc)}개 · 나머지는 표기 · 단위 차이"
)
for r in calc[:2] + [r for r in both(False, True) if r not in calc][:2]:
    print(f"    코드만 {r['id']:4s} 빠진 숫자 {', '.join(r['missing'])} ← {r['sentence'][:46]}")
for r in both(True, False)[:3]:
    print(f"    판사만 {r['id']:4s} ← {r['sentence'][:56]}")
nocite = [r for r in rows if not r["cited"]]
for r in nocite:
    print(f"  출처 없음 {r['id']:4s} ← {r['sentence'][:56]}")
print("\n코드와 판사가 서로 맞는지일 뿐, 둘 중 누가 맞는지는 사람이 읽어야 안다.")
save("eval32_grounded.json", rows)
print("기록 → data/eval32_grounded.json")
