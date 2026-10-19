"""32편 공용: 에이전트 · RAG 평가 — 26편 실행 기록(traces26.jsonl)을 다시 읽어 재는 함수들.

- 검색: Recall@k(정답 섹션이 상위 k개 안에 하나라도 있나) · MRR(첫 정답 순위의 역수 평균)
- 정답 섹션: 시험지 정답 키(28편 채점기 v3로 고친 키)가 그 회사 사업보고서 어느 섹션에 있나 — 사람이 섹션을 고르지 않는다
- 궤적: 계획(어떤 도구를 몇 번, 무슨 인자로) → 작업 → 작성 → 심판 → 반성
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "sec28"))
from grader import KEYS_FIX, flat  # 28편 코드 채점기 v3

CORPS = {
    "삼성전자": "삼성전자",
    "SK하이닉스": "SK하이닉스",
    "하이닉스": "SK하이닉스",
    "현대자동차": "현대자동차",
}
CORPS |= {"현대차": "현대자동차", "카카오": "카카오"}
MAX_GOLD = (
    5  # 정답 키가 섹션 5곳보다 많이 나오면(예: "환율") 어느 문단이 정답인지 못 정한다 → 검색 채점에서 뺀다
)


def traces():
    return [json.loads(line) for line in (DATA / "traces26.jsonl").open()]


def chunks():
    return [json.loads(line) for line in (DATA / "rag" / "chunks.jsonl").open()]


def corps_in(q):
    return sorted({v for k, v in CORPS.items() if k in q})


def keys_of(x):
    return KEYS_FIX.get(x["id"], x["keys"])


def has_key(keys, text):
    return all(any(flat(k) in flat(text) for k in g) for g in keys)


def gold_sections(x, chs):
    """그 회사 보고서에서 첫 정답 키(사실 · 숫자)가 들어 있는 청크의 섹션. 거절 문항 · 회사가 둘 이상이면 None.
    뒤 키("줄" · "감소" 같은 판단 낱말)는 답에서 볼 것이라 검색 정답에는 쓰지 않는다."""
    keys, cs = keys_of(x), corps_in(x["q"])
    if keys == "refuse" or len(cs) != 1:
        return None
    return sorted({c["section"] for c in chs if c["corp"] == cs[0] and has_key(keys[:1], c["text"])})


def first_hit(ranked, gold):
    """순위표(섹션 목록)에서 처음 정답이 나온 순위(1부터). 없으면 None."""
    return next((i for i, s in enumerate(ranked, 1) if s in gold), None)


def recall_at(ranks, k):
    return sum(r is not None and r <= k for r in ranks) / len(ranks)


def mrr(ranks):
    return sum(1 / r for r in ranks if r) / len(ranks)


def plan(x):
    return next((e["tasks"] for e in x["events"] if e["type"] == "plan"), None)


def report_text(x):
    return " ".join(s["sentence"] for s in x["report"])


def save(name, obj):
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1))


def load(name):
    return json.loads((DATA / name).read_text())


assert first_hit(["a", "b", "c"], {"c"}) == 3 and first_hit(["a"], {"z"}) is None
assert recall_at([1, 3, None, 2], 2) == 0.5 and mrr([1, 2, None, 4]) == (1 + 0.5 + 0.25) / 4
