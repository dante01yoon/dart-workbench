"""33편 공용: 저장된 실행(runs/main.jsonl)을 지금 코드로 다시 채점한다 — 모델 호출 0, 비밀 값 0.

- 회귀 세트(regression): 전에 안정적으로 맞히던 문항. 한 문항이라도 떨어지면 관문을 닫는다.
- 능력 세트(capability): 아직 못 하거나 흔들리는 문항. 점수만 기록하고 막지 않는다.
"""

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "sec28"))
from answer import final_answer
from grader import grade  # 28편 코드 채점기 v3


def runs(name="main"):
    """runs/<name>.jsonl — main은 26편 실행, planner_v2는 34편 다시 돌린 실행"""
    return [json.loads(line) for line in (HERE / "runs" / f"{name}.jsonl").open()]


def check(x, make=final_answer):
    """저장된 모델 출력 x → 지금 코드의 최종 답 → 채점(맞으면 True)."""
    text = make(x["report"], x["evidence"])
    return grade(x["keys"], text, x["type"], x["refused"], version=3, qid=x["id"])


def score(xs, make=final_answer):
    return {x["id"]: check(x, make) for x in xs}


def load_env():
    """Langfuse 키(LANGFUSE_PUBLIC_KEY · LANGFUSE_SECRET_KEY)를 .env에서 읽는다 — 화면에 출력하지 않는다. CI는 쓰지 않는다."""
    env = ROOT / ".env"
    for line in env.read_text().splitlines() if env.exists() else []:
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def baseline():
    return json.loads((HERE / "runs" / "baseline.json").read_text())
