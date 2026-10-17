"""2편 ④ 인자 검사: 모델이 잘못된 값을 넣으면 예외로 죽지 않고, 무엇이 틀렸는지 알려 주는 결과를 돌려준다.
사용: uv run python sec02/04_validate.py"""

import json

from tools15 import run_tool

for name, args in [
    ("dividends", {"corp": "삼성", "year": 2023}),
    ("dividends", {"corp": "삼성전자"}),
    ("stock_price", {"corp": "카카오"}),
]:
    print(f"▶ {name}({json.dumps(args, ensure_ascii=False)})")
    print(json.dumps(run_tool(name, args), ensure_ascii=False, indent=1), "\n")
