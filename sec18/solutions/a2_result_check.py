"""과제 2 풀이: 도구 설명은 그대로인데 '결과'에 모델에게 시키는 말이 섞여 오면? — 해시 고정으로는 못 막는다.
guard.clean_result로 결과 글에서 지시 문장을 지운다. 모델 없이 시험 서버(v2_result)만 쓴다.
uv run python sec18/solutions/a2_result_check.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from guard import clean_result
from probe import META

p = subprocess.Popen(
    [sys.executable, str(HERE / "test_server.py")],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
    env={**os.environ, "DEMO_SCENARIO": "v2_result"},
)
args = {"query": "최대주주", "corp": "카카오", "k": 3}
req = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {"_meta": META, "name": "search_filings", "arguments": args},
}
out, _ = p.communicate(json.dumps(req, ensure_ascii=False) + "\n", timeout=120)
text = json.loads(out.splitlines()[0])["result"]["content"][0]["text"]
cleaned, hits = clean_result(text)
print(f"결과 {len(text):,}자 · 지시 문장 {len(hits)}개 발견 → 지움")
print("  예:", hits[0] if hits else "-")
print("  지운 뒤 남은 지시 문장:", len(clean_result(cleaned)[1]))
