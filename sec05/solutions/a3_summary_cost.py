"""과제 3 풀이: 요약 압축은 토큰이 적은데 왜 비용이 더 들까? data/long_task.json에서 요약 호출 비용을 떼어 본다.
먼저 본편 01_long_task.py를 실행해 둔다. 사용: uv run python sec05/solutions/a3_summary_cost.py"""

import json

from _lab import lt

for r in json.loads((lt.ROOT / "data" / "long_task.json").read_text()):
    s = r.get("summary_cost", 0)
    print(
        f"{r['strategy']:13s} 총 ${r['cost']:.4f} = 에이전트 호출 ${r['cost'] - s:.4f} + 요약 호출 ${s:.4f}"
        f"  ({r['turns']}턴, 총 입력 {r['total_prompt_tokens']:,})"
    )
