"""26편 ③ 묶기 → 세기 — 메모를 비슷한 실패끼리 묶어 유형표를 만들고, 전이 실패 행렬을 그린다.

- 묶기: 메모만 모델에게 주고 유형 초안을 받는다(호출 1번). 사람이 화면에서 확인한다. 같은 메모면 저장된 묶음을 다시 쓴다.
- 세기: 유형마다 문항 수. 많은 유형부터 고친다.
- 전이 실패 행렬: 행 = 마지막으로 잘 된 단계, 열 = 처음 틀어진 단계. 기록의 시각 순서로 "바로 앞에서 잘 된 단계"를 찾는다.
사용: uv run python sec26/03_group.py → data/groups26.json · http://127.0.0.1:8830
"""

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sec23"))
sys.path.insert(0, str(ROOT / "sec09"))
from context import chat  # 9편 모델 호출(OpenRouter)
from page import page, serve

TRACES = {x["id"]: x for x in (json.loads(line) for line in (ROOT / "data" / "traces26.jsonl").open())}
MEMOS = json.loads((ROOT / "data" / "memos26.json").read_text())
OUT = ROOT / "data" / "groups26.json"
AGENT = ["계획", "공시 검색", "재무 조회", "뉴스 검색", "작성", "심판"]
ROWS = ["시작", "계획", "공시 검색", "재무 조회", "뉴스 검색", "작성"]
WORKER = {"filings": "공시 검색", "financials": "재무 조회", "news": "뉴스 검색"}
PROMPT = """아래는 AI 리서치 에이전트의 답을 사람이 읽고 단 메모다(문항 id: 메모).
비슷한 실패끼리 4~7개 유형으로 묶어라. 유형 이름은 짧은 한국어 명사구(예: "공시에서 못 찾음").
모든 id가 정확히 한 유형에 들어가야 한다. 문제가 없다는 메모는 "문제 없음"으로 묶는다.
JSON만: {"groups": [{"name": "...", "ids": ["q01"]}]}"""


def group():
    blob = "\n".join(f"{i}: {m['memo']}" for i, m in MEMOS.items())
    sig = hashlib.sha256(blob.encode()).hexdigest()[:12]
    if OUT.exists() and json.loads(OUT.read_text())["sig"] == sig:
        print("같은 메모 → 저장된 묶음을 다시 씀(모델 호출 없음)")
        return json.loads(OUT.read_text())["groups"]
    raw, u = chat(f"{PROMPT}\n\n{blob}", max_tokens=6000)
    cost = float(u.get("cost") or 0)
    if (
        "{" not in raw
    ):  # Flash가 생각하느라 한도를 다 쓰면 빈 답 → 한도를 늘려 한 번 더(12편 Team.llm과 같은 대응)
        print("빈 답 → 한도를 늘려 다시 부름")
        raw, u = chat(f"{PROMPT}\n\n{blob}", max_tokens=18000)
        cost += float(u.get("cost") or 0)
    j = json.loads(raw[raw.index("{") : raw.rindex("}") + 1])
    groups, seen = [], set()
    for g in j["groups"]:
        ids = [i for i in g["ids"] if i in MEMOS and i not in seen]
        seen.update(ids)
        if ids:
            groups.append({"name": g["name"], "ids": ids})
    if MEMOS.keys() - seen:  # 모델이 빠뜨린 메모는 버리지 않고 따로 둔다
        groups.append({"name": "묶이지 않음", "ids": sorted(MEMOS.keys() - seen)})
    print(f"모델이 묶음 초안을 냈어요 · ${cost:.4f}")
    OUT.write_text(json.dumps({"sig": sig, "groups": groups}, ensure_ascii=False, indent=1))
    return groups


def last_ok(x, stage):
    """처음 틀어진 단계 바로 앞에서 잘 된 단계 — 작업은 동시에 돌므로 끝난 시각 순서로 본다."""
    ev = x["events"]
    plan = next((e for e in ev if e["type"] == "plan"), None)
    if stage == "계획" or not plan:
        return "시작"
    if stage == "심판":
        return "작성"
    tasks = {t["id"]: t for t in plan["tasks"]}
    ends = [e for e in ev if e["type"] == "task_end"]
    if stage == "작성":
        good = [e for e in ends if e["n"]]
    else:  # 그 담당의 작업이 끝나기 전에 잘 끝난 다른 작업
        mine = [e for e in ends if WORKER[tasks[e["id"]]["worker"]] == stage]
        cut = min((e["t"] for e in mine if not e["n"]), default=mine[0]["t"] if mine else 1e9)
        good = [e for e in ends if e["n"] and e["t"] < cut and WORKER[tasks[e["id"]]["worker"]] != stage]
    return WORKER[tasks[max(good, key=lambda e: e["t"])["id"]]["worker"]] if good else "계획"


def board(groups):
    total = len(MEMOS)
    rows = "".join(
        f"<tr><td>{g['name']}</td><td class=num>{len(g['ids'])}</td>"
        f"<td><div style='background:#f2b84b;height:22px;width:{len(g['ids']) * 640 // total}px;border-radius:4px'></div></td>"
        f"<td style='font-size:18px'>{' '.join(g['ids'])}</td></tr>"
        for g in sorted(groups, key=lambda g: -len(g["ids"]))
    )
    cells = Counter(
        (last_ok(TRACES[i], m["stage"]), m["stage"]) for i, m in MEMOS.items() if m["stage"] in AGENT
    )
    mx = max(cells.values(), default=1)
    head = "".join(f"<th>{c}</th>" for c in AGENT)
    mat = "".join(
        f"<tr><th>{r}</th>"
        + "".join(
            f"<td class=num style='text-align:center;background:rgba(239,122,107,{cells[(r, c)] / mx:.2f})'>{cells[(r, c)] or ''}</td>"
            for c in AGENT
        )
        + "</tr>"
        for r in ROWS
    )
    col = Counter(m["stage"] for m in MEMOS.values() if m["stage"])
    foot = " · ".join(f"{c} {col[c]}" for c in AGENT + ["채점기", "정답 키"] if col[c])
    return page(
        "실패 유형표",
        f"<h1>실패 유형표 · 메모 {total}개</h1><p class=sub>메모 → 묶기(모델 초안, 사람 확인) → 세기</p>"
        f"<table><tr><th>유형</th><th>문항 수</th><th></th><th>문항</th></tr>{rows}</table>"
        "<h2>전이 실패 행렬 — 행: 마지막으로 잘 된 단계 · 열: 처음 틀어진 단계</h2>"
        f"<table style='width:auto'><tr><th></th>{head}</tr>{mat}</table>"
        f"<p class=sub>처음 틀어진 단계 합계: {foot}</p>",
    )


if __name__ == "__main__":
    groups = group()
    for g in sorted(groups, key=lambda g: -len(g["ids"])):
        print(f"{len(g['ids']):3d}  {g['name']}  ({' '.join(g['ids'])})")
    col = Counter(m["stage"] for m in MEMOS.values() if m["stage"])
    print("처음 틀어진 단계:", " · ".join(f"{k} {v}" for k, v in col.most_common()))
    serve(board(groups), 8830)
