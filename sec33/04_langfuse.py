"""33편 ④ 같은 평가를 Langfuse로 옮기기 — 로컬에 띄운 Langfuse v2(docker, 127.0.0.1:3300)에 데이터셋 · 실행 · 점수를 올리고 다시 읽어 비교.

- 데이터셋 dart-dev-v2: 26편 53문항(질문 · 정답 키 · 회귀/능력 세트)
- 실행 main: 문항마다 트레이스 하나(질문 → 저장된 최종 답) + 점수 correct(우리 코드 채점기 v3가 매긴 0/1)
- 채점기는 옮기지 않는다 — 우리 함수가 매긴 점수를 Langfuse에 기록만 한다. 모델 호출 0.
- 같은 id로 다시 올리면 덮어쓴다(두 번 돌려도 중복이 안 생긴다).
준비: docker compose -f sec33/langfuse/docker-compose.yml up -d (README) · 키는 셸 환경 변수에서만 읽는다.
사용: uv run --with "langfuse>=2.60,<3" python sec33/04_langfuse.py [실행 이름]
"""

import base64
import json
import os
import sys
import time
import urllib.request

from answer import final_answer
from langfuse import Langfuse
from regress import runs, score

HOST = os.environ.setdefault("LANGFUSE_HOST", "http://127.0.0.1:3300")
RUN = sys.argv[1] if len(sys.argv) > 1 else "main"
DS = "dart-dev-v2"
xs = runs()
ok = score(xs)
lf = Langfuse()  # LANGFUSE_PUBLIC_KEY · LANGFUSE_SECRET_KEY를 환경 변수에서 읽는다

t0 = time.time()
lf.create_dataset(name=DS, description="DART 리서치 워크벤치 개발 문항(26편 실행 53문항)")
for x in xs:
    lf.create_dataset_item(dataset_name=DS, id=x["id"], input={"q": x["q"]},
                           expected_output={"keys": x["keys"]}, metadata={"split": x["split"], "type": x["type"]})  # fmt: skip
for item in lf.get_dataset(DS).items:
    x = next(r for r in xs if r["id"] == item.id)
    trace = lf.trace(id=f"{RUN}-{x['id']}", name="dart-research", input=x["q"], public=True,
                     output=final_answer(x["report"], x["evidence"]), metadata={"cost": x["cost"], "seconds": x["seconds"]})  # fmt: skip
    trace.score(
        id=f"{RUN}-{x['id']}-correct", name="correct", value=float(ok[x["id"]]), comment="코드 채점기 v3"
    )
    item.link(trace, run_name=RUN)
lf.flush()
print(
    f"Langfuse({HOST})에 올림 — 데이터셋 {DS} {len(xs)}문항 · 실행 {RUN} · 점수 correct · {time.time() - t0:.1f}초"
)


def get(path):
    auth = base64.b64encode(
        f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()
    ).decode()
    req = urllib.request.Request(HOST + path, headers={"Authorization": "Basic " + auth})
    return json.load(urllib.request.urlopen(req))


got = {}
for page in range(1, 5):  # 다시 읽어 오기: 이 실행의 트레이스에 붙은 점수
    data = get(f"/api/public/scores?name=correct&limit=100&page={page}")["data"]
    got |= {
        s["traceId"].removeprefix(f"{RUN}-"): s["value"] for s in data if s["traceId"].startswith(f"{RUN}-")
    }
    if len(data) < 100:
        break
run = get(f"/api/public/datasets/{DS}/runs/{RUN}")
print(f"다시 읽어 옴 — 실행 {RUN}의 항목 {len(run['datasetRunItems'])}개 · 점수 {len(got)}개")
for split in ("regression", "capability"):
    ids = [x["id"] for x in xs if x["split"] == split]
    print(
        f"  {'회귀' if split == 'regression' else '능력'} 세트  우리 {sum(ok[i] for i in ids)}/{len(ids)} · Langfuse {sum(got.get(i, 0) for i in ids):.0f}/{len(ids)}"
    )
print(f"  전체  우리 {sum(ok.values())}/{len(xs)} · Langfuse 평균 {sum(got.values()) / len(got):.3f}")
print(f"트레이스 보기(로그인 없이 공개 보기) → {HOST}/project/dart-eval/traces/{RUN}-n11")
