"""3편 ③ 캐시와 호출 한도. OpenDART 키는 하루 약 2만 건을 넘기면 status 020(요청 제한 초과)을 돌려준다.
공시는 한 번 나오면 바뀌지 않으니, 같은 도구·같은 인자의 결과는 디스크에 저장해 다시 쓴다.
하루 호출 수도 세어서 한도에 가까우면 실제 호출을 멈추고, 그 사실을 모델에게 결과로 알려 준다.
사용: uv run python sec03/03_cache.py            (같은 질문 4개를 두 번 돌려 실제 호출 수를 비교)
      DAILY_LIMIT=0 uv run python sec03/03_cache.py "SK하이닉스 2025년 직원 수"   (한도에 닿았을 때)
"""

import hashlib
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec02"))
import agent
from tools40 import ROOT, run_tool

CACHE = ROOT / "data" / "cache"
COUNTER = ROOT / "data" / "dart_calls.json"
DAILY_LIMIT = int(os.environ.get("DAILY_LIMIT", "19000"))  # 2만 건보다 조금 낮게 멈춘다
stats = {"api": 0, "hit": 0, "tool_s": 0.0}


def cached_run_tool(name: str, args: dict) -> dict:
    raw = json.dumps([name, args], sort_keys=True, ensure_ascii=False)
    key = hashlib.sha256(raw.encode()).hexdigest()[:16]
    path = CACHE / f"{name}-{key}.json"
    if path.exists():
        stats["hit"] += 1
        return json.loads(path.read_text())
    counts = json.loads(COUNTER.read_text()) if COUNTER.exists() else {}
    today = date.today().isoformat()
    if counts.get(today, 0) >= DAILY_LIMIT:
        return {
            "error": f"오늘 OpenDART 호출 한도({DAILY_LIMIT:,}건)에 닿아 새로 조회하지 않았습니다. 저장된 결과로만 답하세요."
        }
    t0 = time.time()
    result = run_tool(name, args)
    stats["api"] += 1
    stats["tool_s"] += time.time() - t0
    COUNTER.parent.mkdir(exist_ok=True)
    COUNTER.write_text(json.dumps({today: counts.get(today, 0) + 1}))
    if "OpenDART 020" in result.get("error", ""):
        return {
            "error": "OpenDART 요청 제한 초과(020). 오늘은 새로 조회할 수 없습니다. 저장된 결과로만 답하세요."
        }
    if "error" not in result:  # 오류는 저장하지 않는다
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False))
    return result


agent.run_tool = cached_run_tool
QS = sys.argv[1:] or [
    "카카오 2025년 주당 배당금은?",
    "삼성전자 2025년 영업이익은?",
    "현대자동차 2025년 최대주주 지분율은?",
    "SK하이닉스 2025년 감사의견은?",
]
for rnd in (1, 2) if len(sys.argv) == 1 else (1,):
    stats.update(api=0, hit=0, tool_s=0.0)
    t0 = time.time()
    for q in QS:
        answer = agent.run(q)
        print(f"  {q} → {answer.strip().splitlines()[0][:60]}")
    print(
        f"■ {rnd}회차: OpenDART 실제 호출 {stats['api']}번 · 캐시 {stats['hit']}번 · "
        f"도구 시간 {stats['tool_s']:.1f}초 · 전체 {time.time() - t0:.1f}초\n"
    )
counts = json.loads(COUNTER.read_text()) if COUNTER.exists() else {}
print(f"오늘 누적 호출 {counts.get(date.today().isoformat(), 0):,} / 한도 {DAILY_LIMIT:,}")
