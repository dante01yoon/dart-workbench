"""과제 1 풀이: 도구 40개 · 도구 검색 켬에서 틀린 질문을 서버 안내문(instructions)과 도구 설명으로 고친다.
Claude Code 문서: 도구 검색을 쓰면 서버 안내문이 '언제 이 서버의 도구를 찾을지' 알려 주는 역할을 한다.
사용: uv run python sec16/solutions/a1_descriptions.py   (claude -p 40번, 약 4분)
"""

import importlib.util
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("tc", HERE.parent / "03_tool_count.py")
tc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tc)

rows = {}
for better in (False, True):
    if better:
        os.environ["BETTER_DESC"] = "1"  # tools_n.py가 읽는다(claude가 띄우는 서버에 그대로 넘어간다)
    with ThreadPoolExecutor(4) as ex:
        rows[better] = list(ex.map(lambda qw: tc.run(40, True, *qw), tc.Q))
    os.environ.pop("BETTER_DESC", None)

for better, g in rows.items():
    ok = sum(r["ok"] for r in g)
    tok = sum(r["first_prompt"] for r in g) / len(g)
    print(
        f"{'설명 고침' if better else '그대로':>6}: 맞은 도구 {ok}/20 · 첫 입력 토큰 {tok:,.0f} · 평균 턴 {sum(r['turns'] or 0 for r in g) / 20:.1f}"
    )
    for r in g:
        if not r["ok"]:
            print(f"    {r['q']} → {r['picked']} (정답 {r['want']})")
(tc.ROOT / "data" / "cc_desc_fix.json").write_text(json.dumps(rows[True], ensure_ascii=False, indent=1))
