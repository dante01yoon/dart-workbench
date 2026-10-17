"""과제 2 풀이: 작은 모델이 헷갈린 도구 짝의 설명에 "언제 쓰나 · 언제 쓰지 않나"를 더하고 다시 잰다.
헷갈린 짝: key_accounts ↔ financial_ratios ↔ all_financial_statements (영업이익·자산총계 질문)
사용: uv run python sec03/solutions/a2_descriptions.py [모델]"""

import copy
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from select_lab import REPEAT, Q, pick
from tools40 import TOOLS15, TOOLS40

BETTER = {
    "key_accounts": "주요 계정 요약: 매출액·영업이익·당기순이익·자산총계·부채총계·자본총계 금액(당기·전기, 원). "
    "이 대표 숫자들을 물으면 가장 먼저 쓴다.",
    "financial_ratios": "재무 비율(%)만: 영업이익률·ROE 같은 수익성 비율. 금액(원)이 필요하면 key_accounts를 쓴다.",
    "all_financial_statements": "전체 재무제표의 세부 계정 금액: 감가상각비·재고자산처럼 key_accounts에 없는 계정일 때만 쓴다. "
    "account에 계정 이름 일부를 넣어 거른다.",
}


def patched(tools):
    out = copy.deepcopy(tools)
    for t in out:
        if t["function"]["name"] in BETTER:
            t["function"]["description"] = BETTER[t["function"]["name"]]
    return out


model = sys.argv[1] if len(sys.argv) > 1 else "qwen/qwen3.5-9b"
for label, tools in (
    ("15개 · 원래 설명", TOOLS15),
    ("15개 · 고친 설명", patched(TOOLS15)),
    ("40개 · 원래 설명", TOOLS40),
    ("40개 · 고친 설명", patched(TOOLS40)),
):
    qs = Q * REPEAT
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda x, t=tools: pick(model, t, x[0]), qs))
    ok = sum(g == w for (g, _, _), (_, w) in zip(res, qs))
    fin = [(g, w) for (g, _, _), (_, w) in zip(res, qs) if w in BETTER]
    fin_ok = sum(g == w for g, w in fin)
    print(f"{label:14s} 정확도 {ok / len(qs):.2f}  재무 3도구 문항 {fin_ok}/{len(fin)}")
