"""11편 ③ 직접 구현 vs LangChain vs LlamaIndex — 같은 청크 · 같은 임베딩 · 같은 38문항 × 2벌 · 회사 필터.
recall@5와 검색 코드 줄 수, 준비 시간, 문항당 시간을 잰다. 프레임워크의 기본 토크나이저(띄어쓰기)도 한 줄 넣는다.
사용: uv run --group frameworks python sec11/03_compare.py → data/rag/frameworks.json"""

import ast
import inspect
import json
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")  # langchain-community 지원 종료 예정 경고

t0 = time.time()
import lc

LC_BUILD = time.time() - t0
t0 = time.time()
import li

LI_BUILD = time.time() - t0
import search
from search import BM25, DIR, doc_text, embed, eval_questions, first_hit, keyword, rrf, unit, vector

HERE = Path(__file__).resolve().parent


def code_lines(src):
    """빈 줄 · 주석 · 문서 문자열을 뺀 코드 줄 수."""
    tree = ast.parse(src)
    doc = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (
            isinstance(body, list)
            and body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
        ):
            doc |= set(range(body[0].lineno, body[0].end_lineno + 1))
    return sum(
        1
        for n, line in enumerate(src.splitlines(), 1)
        if line.strip() and not line.strip().startswith("#") and n not in doc
    )


def search_part(path):
    """프레임워크 파일에서 검색 부분(답 함수 앞까지)만 센다."""
    src = path.read_text(encoding="utf-8")
    return code_lines(src.split("\nLLM = ")[0])


OWN_SRC = "\n\n".join(
    inspect.getsource(f) for f in (search.bigrams, BM25, doc_text, search.allowed, keyword, vector, rrf)
)
LINES = {
    "직접": code_lines(OWN_SRC),
    "LangChain": search_part(HERE / "lc.py"),
    "LlamaIndex": search_part(HERE / "li.py"),
}
print(
    f"검색 코드 줄 수  직접 {LINES['직접']} · LangChain {LINES['LangChain']} · LlamaIndex {LINES['LlamaIndex']}"
)
print(f"준비 시간  LangChain {LC_BUILD:.1f}초 · LlamaIndex {LI_BUILD:.1f}초")

chunks, emb = lc.CHUNKS, lc.EMB
bm = BM25([doc_text(c) for c in chunks])
qs = eval_questions()
rows = []


def own(text, corp, v, kind):
    kw, ve = keyword(bm, chunks, text, 50, corp), vector(emb, chunks, v, 50, corp)
    return {"keyword": kw, "vector": ve, "hybrid": rrf(kw, ve, k=10)}[kind][:10]


IMPLS = {  # (검색 함수, 2글자 토큰)
    "직접": (own, True),
    "LangChain": (lambda text, corp, v, kind: lc.search(text, kind, corp), True),
    "LlamaIndex": (lambda text, corp, v, kind: li.search(text, kind, corp), True),
    "LangChain 기본 토크나이저": (
        lambda text, corp, v, kind: lc.search(text, kind, corp, korean=False),
        False,
    ),
    "LlamaIndex 기본 토크나이저": (
        lambda text, corp, v, kind: li.search(text, kind, corp, korean=False),
        False,
    ),
}
for field, label in (("q", "원래"), ("q_para", "말 바꿈")):
    qv = unit(embed([q[field] for q in qs])[0])
    for name, (fn, korean) in IMPLS.items():
        kinds = ("keyword", "vector", "hybrid") if korean else ("keyword",)
        line = f"{label:4s} {name:22s}"
        for kind in kinds:
            t0 = time.time()
            hits = [first_hit(chunks, fn(q[field], q["corp"], v, kind), q) for q, v in zip(qs, qv)]
            rec = sum(h is not None and h < 5 for h in hits) / len(qs)
            rows.append(
                {
                    "set": label,
                    "impl": name,
                    "kind": kind,
                    "recall@5": round(rec, 3),
                    "sec_per_q": round((time.time() - t0) / len(qs), 3),
                }
            )
            line += f"  {kind} {rec:.3f}"
        print(line, flush=True)
(DIR / "frameworks.json").write_text(
    json.dumps(
        {
            "lines": LINES,
            "build": {"LangChain": round(LC_BUILD, 1), "LlamaIndex": round(LI_BUILD, 1)},
            "rows": rows,
        },
        ensure_ascii=False,
    )
)
print("저장 → data/rag/frameworks.json   비교 화면: uv run python sec11/04_compare_web.py")
