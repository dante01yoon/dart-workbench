"""하네스 (강의 1편): 모든 LLM 호출을 기록하고, 평가 실행 한 번을 성적표 한 줄로 남긴다.

    with Trace("hybrid+rerank") as tr:      # 이 블록 안의 모든 chat() 호출이 기록된다
        ...
    tr.summary()  → 호출 수·토큰·비용($)·지연 p50/p95
성적표: data/scorecard.jsonl 에 한 줄씩 쌓는다(웹 화면 /scorecard 가 읽는다).
"""

import json
import statistics
import threading
import time
from contextlib import ContextDecorator

from . import dart

SCORECARD = dart.ROOT / "data" / "scorecard.jsonl"
_local = threading.local()
_active = []  # 열려 있는 Trace들(스레드 풀 워커의 호출도 잡기 위해 전역)
_lock = threading.Lock()


def record(model, usage, seconds):
    """answer.chat()이 호출마다 부른다."""
    call = {"model": model, "seconds": round(seconds, 3), "prompt": usage.get("prompt_tokens", 0),
            "completion": usage.get("completion_tokens", 0), "cost": float(usage.get("cost") or 0)}
    with _lock:
        for tr in _active:
            tr.calls.append(call)


class Trace(ContextDecorator):
    def __init__(self, name):
        self.name, self.calls, self.items = name, [], []

    def __enter__(self):
        self.t0 = time.time()
        with _lock:
            _active.append(self)
        return self

    def __exit__(self, *exc):
        self.seconds = time.time() - self.t0
        with _lock:
            _active.remove(self)
        return False

    def item(self, qid, ok, seconds):
        """평가 문항 하나의 결과(통과 여부, 걸린 시간)."""
        self.items.append({"id": qid, "ok": bool(ok), "seconds": round(seconds, 3)})

    def summary(self):
        lat = sorted(i["seconds"] for i in self.items) or [0]
        n = len(self.items) or 1
        return {
            "name": self.name, "date": time.strftime("%Y-%m-%d %H:%M"),
            "n": len(self.items), "pass_rate": round(sum(i["ok"] for i in self.items) / n, 3),
            "calls": len(self.calls),
            "tokens": sum(c["prompt"] + c["completion"] for c in self.calls),
            "cost_usd": round(sum(c["cost"] for c in self.calls), 4),
            "cost_per_q": round(sum(c["cost"] for c in self.calls) / n, 5),
            "p50_s": round(statistics.median(lat), 2),
            "p95_s": round(lat[min(len(lat) - 1, int(len(lat) * 0.95))], 2),
        }

    def save(self, **extra):
        row = {**self.summary(), **extra}
        with SCORECARD.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row
