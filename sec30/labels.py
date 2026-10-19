"""30편 사람 라벨 — 라벨링 지침 v1(27편 루브릭에서) · 라벨 한 줄의 모양 · 26편 메모에서 만든 검토 라벨.

라벨 한 줄: 문항 id · 기준(전체 / R2 / R6) · 통과/실패/보류 · 이유(자유 글) · 처음 틀어진 단계 · 라벨러 · 지침 버전 · 근거(어디서 왔나).
검토 라벨: 26편 메모 14개(단테 2026-10-19 검토 "수정 없음, 그대로 승인"). 메모가 없는 39문항은 "읽었고 메모할 문제 없음"으로 본
암묵 통과 — 단테가 하나씩 확인한 라벨은 아니라서 source를 따로 적는다.
사용: uv run python sec30/labels.py → data/labels30.json
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TRACES = {x["id"]: x for x in map(json.loads, (DATA / "traces26.jsonl").open())}
MEMOS = json.loads((DATA / "memos26.json").read_text())
AGENT = {"계획", "공시 검색", "재무 조회", "뉴스 검색", "작성", "심판"}  # 에이전트 안 단계(28편과 같음)

# 라벨링 지침 v1 — 27편 루브릭 v1의 기준 문장을 라벨러가 읽는 말로. 바뀌면 버전을 올리고 영향받는 라벨을 다시 단다.
GUIDE = {
    "version": "v1 (27편 루브릭, 2026-10-19)",
    "전체": "사용자가 이 답을 그대로 믿어도 되나? 핵심 값이 공시와 같고, 빠진 항목이 없고, 공시에 없는 값은 없다고 밝혔으면 통과.",
    "R2": "질문이 묻는 항목(명단 · 부문 · 두 회사)을 모두 답했나? 하나라도 빠지면 실패.",
    "R6": "답의 문장마다 근거(원문 인용)에 그 내용이 있나? 근거에 없는 숫자 · 사실을 덧붙였으면 실패. 요약(claim)만 보지 말고 원문 인용을 본다.",
    "보류": "지침으로 정할 수 없으면 보류 + 이유. 보류가 쌓이면 지침을 고칠 신호다.",
    "단계": "실패면 처음 틀어진 단계 하나: 계획 · 공시 검색 · 재무 조회 · 뉴스 검색 · 작성 · 채점기",
}

# R2 라벨은 메모 문장에서 읽었다(어느 구절에서 읽었는지 같이 둔다). 29편 R2 14문항 중 메모가 없는 문항은 암묵 통과.
R2_FROM_MEMO = {
    "n07": (False, "9명 중 4명만 찾음"),
    "n09": (False, "뉴스로 50억 이상만 말함"),
    "n15": (False, "플랫폼·콘텐츠 구분이 없음"),
    "q32": (False, "보고서는 문장 0개"),
    "q38": (False, "매출·이익만 답함(주당 배당금 없음)"),
    "q45": (True, "통화 4개는 맞음"),
}
R2_IDS = ["q36", "q45", "n01", "n07", "n09", "n10", "n15", "n16", "n17", "n18", "q35", "q32", "q33", "q38"]  # fmt: skip


def label(qid, crit, ok, reason, source, stage=""):
    return {"id": qid, "criterion": crit, "label": "통과" if ok else "실패", "reason": reason, "stage": stage,
            "labeler": "단테", "guide": GUIDE["version"], "source": source}  # fmt: skip


def build():
    out = []
    # 전체 통과/실패: 28편 01_regrade와 같은 규칙(q45는 정답은 맞고 덧붙인 문장 문제라 전체는 통과)
    for qid in TRACES:
        m = MEMOS.get(qid)
        if m:
            ok = not (m["stage"] in AGENT and qid != "q45")
            out.append(label(qid, "전체", ok, m["memo"], "메모 · 단테 검토 10/19", m["stage"]))
        else:
            out.append(label(qid, "전체", True, "", "암묵 통과(메모 없음)"))
    for qid in R2_IDS:
        ok, why = R2_FROM_MEMO.get(qid, (True, ""))
        out.append(
            label(qid, "R2", ok, why, "메모에서 읽음 · 단테 검토 10/19" if why else "암묵 통과(메모 없음)")
        )
    return out


def load(crit, explicit_only=False):
    """기준 하나의 라벨 → {id: True(통과)/False(실패)}"""
    rows = json.loads((DATA / "labels30.json").read_text())
    return {
        r["id"]: r["label"] == "통과"
        for r in rows
        if r["criterion"] == crit and not (explicit_only and r["source"].startswith("암묵"))
    }


if __name__ == "__main__":
    rows = build()
    (DATA / "labels30.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    for crit in ("전체", "R2"):
        rs = [r for r in rows if r["criterion"] == crit]
        exp = [r for r in rs if not r["source"].startswith("암묵")]
        print(f"{crit}: {len(rs)}문항 — 실패 {sum(r['label'] == '실패' for r in rs)} · 통과 {sum(r['label'] == '통과' for r in rs)}"
              f" (메모로 단 라벨 {len(exp)} · 암묵 통과 {len(rs) - len(exp)})")  # fmt: skip
    print("→ data/labels30.json")
