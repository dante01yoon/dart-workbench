"""10편 공용: 문장마다 출처를 다는 답, 인용 확인, 숫자를 재무 API 값과 대조, 근거 없음 · 투자 권유 거절.

검색은 9편의 맥락 붙인 하이브리드(키워드 + 벡터 RRF)를 그대로 쓴다.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec09"))
import numpy as np
from context import DIR, chat, load_context  # 9편 → 8편 → 7편 공용 모듈을 그대로 쓴다
from search import BM25, doc_text, embed, keyword, load_store, rrf, unit, vector
from tools15 import ROOT, run_tool

NO_EVIDENCE = "근거 없음: 사업보고서에서 찾지 못했습니다."
NO_ADVICE = "투자 권유 거절: 투자 판단은 도와드릴 수 없습니다."
PROMPT = f"""아래 사업보고서 발췌만 근거로 질문에 답하라.
규칙
1. 문장마다 끝에 근거 발췌 번호를 [1]처럼 단다. 근거 없는 문장은 쓰지 않는다.
2. 숫자는 발췌에 적힌 그대로(단위 포함) 옮긴다. 계산한 값이면 "계산:"으로 시작하고 쓴 숫자의 출처를 단다.
3. 발췌에 답할 근거가 없으면 이 한 줄만 쓴다: {NO_EVIDENCE}
4. 주식을 사라·팔라, 주가 전망, 투자처 추천을 묻는 질문이면 이 한 줄만 쓴다: {NO_ADVICE}

질문: {{q}}

{{ctx}}"""


class Store:
    """청크 · 맥락 붙인 BM25 · 맥락 붙인 벡터를 한 번만 읽어 둔다."""

    def __init__(self):
        self.chunks, _ = load_store()
        ctx = load_context()
        self.bm = BM25([ctx.get(c["id"], "") + " " + doc_text(c) for c in self.chunks])
        self.emb = unit(np.load(DIR / "emb_ctx.npy"))

    def search(self, q, corp=None, k=6):
        qv = unit(embed([q])[0])[0]
        kw = keyword(self.bm, self.chunks, q, 50, corp)
        ve = vector(self.emb, self.chunks, qv, 50, corp)
        return rrf(kw, ve, k=k)


def answer(store, q, corp=None, k=6):
    hits = store.search(q, corp, k)
    ctx = "\n\n".join(
        f"[{n}] ({store.chunks[i]['corp']} · {store.chunks[i]['section']})\n{store.chunks[i]['text']}"
        for n, i in enumerate(hits, 1)
    )
    text, u = chat(PROMPT.format(q=q, ctx=ctx), max_tokens=6000)
    return text or "(빈 답)", hits, float(u.get("cost") or 0)


def kind(text):
    if text.startswith("근거 없음"):
        return "근거 없음"
    if text.startswith("투자 권유 거절"):
        return "투자 거절"
    return "답"


NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def sentences(text):
    """마침표 뒤에 붙은 출처('…입니다. [1]')를 마침표 앞으로 옮긴 뒤 마침표 · 줄바꿈에서 자른다."""
    text = re.sub(r"\.\s*((?:\[\d+\])+)", r" \1.", text)
    return [s.strip() for s in re.split(r"(?<=\.)\s+|\n+", text) if s.strip()]


def check_sentence(s, chunks, hits):
    """문장 하나: 출처 번호가 있나, 번호가 발췌 범위 안인가, 문장의 숫자가 그 발췌에 그대로 있나."""
    refs = [int(x) for x in re.findall(r"\[(\d+)\]", s)]
    if not refs:
        return "출처 없음"
    if any(not 1 <= r <= len(hits) for r in refs):
        return "없는 번호"
    if s.lstrip().startswith("계산"):
        return "계산"
    src = "".join(chunks[hits[r - 1]]["text"] for r in refs).replace(" ", "")
    nums = [n for n in NUM.findall(re.sub(r"\[\d+\]", "", s)) if len(n.replace(",", "")) >= 3]
    missing = [n for n in nums if n not in src]
    return "숫자 불일치 " + ", ".join(missing) if missing else "확인"


def to_won(text):
    """답에 나온 금액들을 원 단위로 바꾼다: '43조 6,010억' · '43,601,051백만원' · '7,320억원' · '732,036,535,379원'."""
    out = []
    for m in re.finditer(r"(\d[\d,]*)\s*조(?:\s*(\d[\d,]*)\s*억)?", text):
        out.append(
            int(m.group(1).replace(",", "")) * 10**12 + int((m.group(2) or "0").replace(",", "")) * 10**8
        )
    for m in re.finditer(r"(?<![조\d,.])(\d[\d,]*(?:\.\d+)?)\s*억", text):  # '4,952.64억'처럼 소수도
        out.append(round(float(m.group(1).replace(",", "")) * 10**8))
    for m in re.finditer(r"(\d[\d,]{6,})\s*(백만원|백만 원|원)?", text):
        v = int(m.group(1).replace(",", ""))
        out.append(v * 10**6 if m.group(2) and "백만" in m.group(2) else v)
    return out


ACCOUNT = {"매출": "매출액", "영업수익": "매출액", "영업이익": "영업이익", "당기순이익": "당기순이익"}


def prior_values(corp, q):
    """2024년 금액은 두 가지다: 2024년 보고서의 당기 값, 2025년 보고서가 다시 쓴 전기 값(재작성)."""
    name = next((v for k, v in ACCOUNT.items() if k in q), None)
    rows = run_tool("key_accounts", {"corp": corp, "year": 2025}).get("rows", [])
    row = next(
        (r for r in rows if r["fs_nm"].startswith("연결") and r["account_nm"].startswith(name or "-")), None
    )
    restated = int(row["frmtrm_amount"].replace(",", "")) if row else None
    return {api_value(corp, 2024, q)[1], restated} - {None}


def api_value(corp, year, q):
    """질문의 계정을 주요 계정 API(연결)에서 찾는다. 카카오는 영업수익을 매출액 칸에 둔다."""
    name = next((v for k, v in ACCOUNT.items() if k in q), None)
    rows = run_tool("key_accounts", {"corp": corp, "year": year}).get("rows", [])
    row = next(
        (r for r in rows if r["fs_nm"].startswith("연결") and r["account_nm"].startswith(name or "-")), None
    )
    return (name, int(row["thstrm_amount"].replace(",", ""))) if row else (name, None)


def match_api(text, value, tol=0.001):
    """답의 금액 중 하나가 API 값과 0.1% 안으로 맞으면 통과(억 단위 반올림 허용)."""
    return any(abs(v - value) <= value * tol for v in to_won(text))


def questions():
    return {json.loads(line)["id"]: json.loads(line) for line in (ROOT / "eval" / "questions.jsonl").open()}


def keys():
    return json.loads((ROOT / "eval" / "answer_keys.json").read_text())


def flat(s):
    return "".join(s.split())


def correct(text, key):
    if key == "refuse":
        return kind(text) != "답"
    return kind(text) == "답" and all(any(flat(k) in flat(text) for k in g) for g in key)
