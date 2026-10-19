"""33편 ⓪ 저장된 실행 얼리기 — 26편 실행 기록에서 CI가 쓸 것만 꺼내 runs/main.jsonl로 저장하고, 회귀 · 능력 세트를 나눈다.

- 넣는 것: 질문 · 정답 키 · 보고서 문장 · 근거 카드 요약(모델이 쓴 글) · 판사 배지 · 반성 여부 · 비용 · 시간.
  공시 원문 인용(quote)과 검색 결과는 넣지 않는다 → 공개 저장소에 올려도 된다.
- 회귀 세트 = 26편에서 맞았고, 10/18 세 번 돌리기에도 있던 문항이면 세 번 모두 맞은 것.
  (세 번 기록이 없는 문항은 한 번만 보고 넣었다 — 한계)
- 기준 점수(runs/baseline.json) = 지금 answer.py로 채점한 문항별 결과.
사용(로컬, data/ 필요): uv run python sec33/00_freeze.py
"""

import json
from collections import defaultdict

from regress import HERE, ROOT, grade, score  # grade = 28편 코드 채점기 v3

DATA = ROOT / "data"
traces = [json.loads(line) for line in (DATA / "traces26.jsonl").open()]
rows = [
    {
        **{k: x[k] for k in ("id", "q", "type", "keys", "refused", "cost", "seconds")},
        "report": [s["sentence"] for s in x["report"]],
        "evidence": [e["claim"] for e in x.get("evidence", [])],
        "badges": [s.get("badge") for s in x["report"]],
        "reflected": any(e["type"] == "revise" for e in x["events"]),
    }
    for x in traces
]
ok26 = score(rows)

keys = {x["id"]: x for x in rows}
three = defaultdict(list)  # 10/18 같은 20문항 세 번 — 지금 채점기(v3)로 다시 채점
for r in json.loads((DATA / "repeat3_1018.json").read_text()):
    x = keys[r["id"]]
    three[r["id"]].append(grade(x["keys"], r["answer"], x["type"], False, version=3, qid=r["id"]))

for x in rows:
    x["split"] = "regression" if ok26[x["id"]] and all(three.get(x["id"], [True])) else "capability"
(HERE / "runs" / "main.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows))
(HERE / "runs" / "baseline.json").write_text(json.dumps(ok26, indent=1))

reg = [x for x in rows if x["split"] == "regression"]
flaky = [i for i in three if ok26[i] and not all(three[i])]
print(f"26편 실행 {len(rows)}문항 → runs/main.jsonl (공시 원문 인용 없이 모델 출력만)")
print(
    f"  26편에 맞은 문항 {sum(ok26.values())}개 중 세 번 돌리기에서 흔들린 {len(flaky)}개({' '.join(sorted(flaky))})는 능력 세트로"
)
print(f"  회귀 세트 {len(reg)}문항 · 능력 세트 {len(rows) - len(reg)}문항")
