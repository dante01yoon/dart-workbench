"""33편 ① 회귀 관문 — PR마다 GitHub Actions가 돌린다. 모델 호출 0 · 비밀 값 0 · 몇 초.

저장된 실행(runs/main.jsonl, 26편 53문항의 모델 출력)에 지금 코드의 최종 답 만들기(answer.py) → 코드 채점기 v3.
- 회귀 세트: 문항 하나라도 떨어지면 실패(exit 1). 전체 점수 평균으로 막지 않는다 — 48문항으로 잡을 수 있는
  최소 차이가 17%p(31편)라서, 몇 문항 떨어진 것은 평균 속에 묻힌다.
- 능력 세트: 점수와 기준(main) 대비 변화만 적는다.
- 프롬프트 · 모델을 바꾼 PR은 CI에서 모델을 부르지 않는다(키를 CI에 넣지 않는다) → 로컬에서 다시 돌려 runs/를 갈아 끼운 PR로 올린다.
사용: python sec33/01_gate.py [--runs 이름] [--log 파일 --label 이름]   (--runs 기본 main, 34편은 planner_v2)
"""

import json
import os
import sys

from regress import baseline, runs, score

NAME = sys.argv[sys.argv.index("--runs") + 1] if "--runs" in sys.argv else "main"
xs = runs(NAME)
now, base = score(xs), baseline()
reg = [x for x in xs if x["split"] == "regression"]
cap = [x for x in xs if x["split"] == "capability"]
lost = [x for x in reg if not now[x["id"]]]
n = lambda group, s: sum(s[x["id"]] for x in group)
total, total0 = sum(now.values()), sum(base.values())

print(
    f"회귀 관문 — 저장된 실행 runs/{NAME} {len(xs)}문항 · 지금 코드의 answer.py → 코드 채점기 v3 (모델 호출 0)"
)
print(
    f"  회귀 세트  {n(reg, now)}/{len(reg)}  {'통과' if not lost else '실패'}  (기준: 한 문항도 떨어지면 안 된다)"
)
for x in lost:
    print(f"    ✗ {x['id']}  {x['q'][:34]}")
print(f"  능력 세트  {n(cap, now)}/{len(cap)}  (main {n(cap, base)}/{len(cap)}) — 막지 않고 기록만")
print(
    f"  전체       {total}/{len(xs)} = {total / len(xs):.1%}  (main {total0 / len(xs):.1%}, {(total - total0) / len(xs) * 100:+.1f}%p)"
)
print(f"결과: {'실패 — 회귀 세트에서 ' + str(len(lost)) + '문항이 떨어졌다' if lost else '통과'}")

if os.environ.get("GITHUB_ACTIONS"):  # PR 화면에 보이게: 떨어진 문항마다 오류 표시 + 실행 요약 표
    for x in lost:
        print(f"::error title=회귀 {x['id']}::{x['q']} — main에서는 맞았는데 이 코드에서 틀림")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
        f.write("### 회귀 관문\n| 세트 | 지금 | main |\n|---|---|---|\n")
        f.write(
            f"| 회귀 | {n(reg, now)}/{len(reg)} | {n(reg, base)}/{len(reg)} |\n| 능력 | {n(cap, now)}/{len(cap)} | {n(cap, base)}/{len(cap)} |\n"
        )
        f.write("\n" + ("떨어진 문항: " + ", ".join(x["id"] for x in lost) if lost else "회귀 없음") + "\n")
if "--log" in sys.argv:  # 대시보드용 기록(로컬)
    path, label = sys.argv[sys.argv.index("--log") + 1], sys.argv[sys.argv.index("--label") + 1]
    with open(path, "a") as f:
        f.write(json.dumps({"label": label, "items": now}, ensure_ascii=False) + "\n")
sys.exit(1 if lost else 0)
