"""7편 공용: 사업보고서 → 청크 → 임베딩 → 벡터 검색(numpy). 라이브러리 없이 원리 그대로.

- 청크: 섹션(목차 항목) 안에서 약 SIZE자씩 자른다. 표는 4편처럼 행마다 "칸 | 칸" 한 줄이다.
  표가 잘리면 다음 조각 맨 앞에 "캡션(단위·기간) + 머리 행"을 다시 붙여 숫자가 무슨 열인지 잃지 않게 한다.
- 메타데이터: 회사 · 연도 · 접수번호 · 섹션 경로. 검색할 때 회사·연도로 거를 수 있다.
- 벡터 저장소: data/rag/emb.npy(청크 수 × 1536) 한 파일. 검색은 코사인 유사도 = 정규화한 벡터의 내적.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec04"))
from report import load
from tools15 import ROOT

CORPS = ["삼성전자", "SK하이닉스", "현대자동차", "카카오"]
YEAR = 2025
SIZE = 900
DIR = ROOT / "data" / "rag"


def is_row(line):
    return " | " in line


def cells(line):
    return [c for c in line.split(" | ") if c.strip()]


def chunk_section(lines):
    """섹션 본문(줄 목록) → 청크 글 목록. 표가 잘리면 캡션 + 머리 행을 다시 붙인다."""
    out, buf, head = [], [], []
    for i, line in enumerate(lines):
        if is_row(line) and (i == 0 or not is_row(lines[i - 1])):  # 표의 첫 줄
            cap = lines[i - 1] if i and not is_row(lines[i - 1]) and len(lines[i - 1]) <= 120 else ""
            head = ([cap] if cap else []) + [line]
        elif is_row(line) and len(head) and len(cells(head[-1])) <= 2 and head[-1] == lines[i - 1]:
            head.append(line)  # 첫 줄이 "(단위 : 백만원)" 같은 단위 줄이면 다음 줄(열 이름)까지 머리 행
        elif not is_row(line):
            head = []
        if buf and sum(len(x) + 1 for x in buf) + len(line) > SIZE:
            out.append("\n".join(buf))
            buf = list(head) if is_row(line) and line not in head else []
        buf.append(line)
    if buf:
        out.append("\n".join(buf))
    return [c for c in out if len(c) >= 40]  # "(단위 : 사)" 같은 조각은 뺀다


def build_chunks():
    rows = []
    for corp in CORPS:
        rep = load(corp, YEAR)
        for s in rep["sections"]:
            for text in chunk_section(s["text"].split("\n")):
                rows.append(
                    {
                        "id": len(rows),
                        "corp": corp,
                        "year": YEAR,
                        "rcept_no": rep["rcept_no"],
                        "section": s["title"],
                        "text": text,
                    }
                )
    return rows


def embed(texts, batch=64):
    """OpenRouter 임베딩 API. 돌려받는 것: (벡터 목록, 토큰 수, 비용)."""
    vecs, tokens, cost = [], 0, 0.0
    for i in range(0, len(texts), batch):
        body = json.dumps({"model": os.environ["EMBED_MODEL"], "input": texts[i : i + batch]}).encode()
        req = urllib.request.Request(
            os.environ["OPENAI_BASE_URL"].rstrip("/") + "/embeddings",
            data=body,
            headers={
                "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                "Content-Type": "application/json",
            },
        )
        r = json.load(urllib.request.urlopen(req, timeout=300))
        vecs += [d["embedding"] for d in sorted(r["data"], key=lambda d: d["index"])]
        tokens += r.get("usage", {}).get("prompt_tokens", 0)
        cost += float(r.get("usage", {}).get("cost") or 0)
    return vecs, tokens, cost


def load_store():
    chunks = [json.loads(line) for line in (DIR / "chunks.jsonl").open(encoding="utf-8")]
    emb = np.load(DIR / "emb.npy")
    return chunks, emb / np.linalg.norm(emb, axis=1, keepdims=True)


def search(query, chunks, emb, k=5, corp=None, year=None):
    """질문 벡터와 코사인 유사도가 큰 청크 k개. corp·year를 주면 그 보고서 안에서만 찾는다."""
    q = np.array(embed([query])[0][0])
    scores = emb @ (q / np.linalg.norm(q))
    mask = np.array(
        [(corp is None or c["corp"] == corp) and (year is None or c["year"] == year) for c in chunks]
    )
    scores = np.where(mask, scores, -1)
    return [int(i) for i in np.argsort(-scores)[:k]]


def is_gold(c, q):
    """정답 청크 = 회사가 같고, 섹션 경로에 gold.section이 있고, 본문에 gold.contains 중 하나가 있는 청크."""
    g = q["gold"]
    return (
        c["corp"] == q.get("corp", c["corp"])
        and (not g.get("section") or g["section"] in c["section"])
        and any(s in c["text"] for s in g["contains"])
    )


def scorecard(chunks, emb, qs, qv, use_filter):
    """recall@5 · MRR@10 · 놓친 문항. qv = 질문 벡터(정규화)."""
    rec = mrr = 0
    misses = []
    for q, v in zip(qs, qv):
        s = emb @ v
        if use_filter:
            s = np.where(
                [c["corp"] == q.get("corp", c["corp"]) and c["year"] == q["year"] for c in chunks], s, -1
            )
        top = [int(i) for i in np.argsort(-s)[:10]]
        hit = next((r for r, i in enumerate(top) if is_gold(chunks[i], q)), None)
        rec += hit is not None and hit < 5
        mrr += 1 / (hit + 1) if hit is not None else 0
        if hit is None or hit >= 5:
            misses.append((q["q"], chunks[top[0]]["corp"], chunks[top[0]]["section"]))
    return rec, mrr / len(qs), misses


def eval_questions():
    """2025년 보고서만 넣었으므로 정답 근거가 있는 2025년 문항만."""
    qs = [
        json.loads(line)
        for line in (ROOT / "eval" / "questions.jsonl").open(encoding="utf-8")
        if line.strip()
    ]
    return [q for q in qs if q.get("gold") and q.get("year") == YEAR]


def unit(vecs):
    v = np.array(vecs, dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)
