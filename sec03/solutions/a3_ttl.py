"""과제 3 풀이: 도구마다 캐시 유효기간을 다르게. 사업보고서의 숫자는 한 번 나오면 바뀌지 않지만,
공시 목록(list_filings)은 새 공시가 올라오면 바뀐다 → 하루가 지나면 다시 조회한다.
사용: uv run python sec03/solutions/a3_ttl.py"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools40 import ROOT, run_tool

CACHE = ROOT / "data" / "cache_ttl"
TTL = {"list_filings": 24 * 3600}  # 초. 여기 없는 도구는 영구 저장
calls = []


def cached_run_tool(name, args):
    key = hashlib.sha256(json.dumps([name, args], sort_keys=True).encode()).hexdigest()[:16]
    path = CACHE / f"{name}-{key}.json"  # 파일 이름에 따옴표·한글이 들어가지 않게 해시로
    ttl = TTL.get(name)
    if path.exists() and (ttl is None or time.time() - path.stat().st_mtime < ttl):
        return json.loads(path.read_text())
    calls.append(name)
    result = run_tool(name, args)
    if "error" not in result:
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False))
    return result


A = {"corp": "카카오", "year": 2025}
for name in ("list_filings", "key_accounts"):
    cached_run_tool(name, A)
print("처음 조회         → 실제 호출:", calls)

calls.clear()
for name in ("list_filings", "key_accounts"):
    cached_run_tool(name, A)
print("바로 다시 조회    → 실제 호출:", calls)

two_days_ago = time.time() - 2 * 24 * 3600
for p in CACHE.glob("*.json"):  # 저장한 지 이틀 지난 것처럼 파일 시각을 돌린다
    os.utime(p, (two_days_ago, two_days_ago))
calls.clear()
for name in ("list_filings", "key_accounts"):
    cached_run_tool(name, A)
print("이틀 뒤 다시 조회 → 실제 호출:", calls)
