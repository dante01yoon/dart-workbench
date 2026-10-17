"""과제 2 풀이: 목차·섹션 읽기 없이 find_in_report 하나만 주면? 그리고 찾은 줄의 앞뒤 한 줄을 붙이면?
표의 숫자 줄은 머리 행(연도·단위)과 떨어져 있어서, 줄 하나만 보면 어느 해 숫자인지 모를 수 있다.
사용: uv run python sec04/solutions/a2_find_only.py"""

from _lab import ctx  # sec04를 import 경로에 넣는다

rt, load = ctx.rt, ctx.load


def find_with_context(name, args):
    if name != "find_in_report":
        return rt.run_tool(name, args)
    secs = load(args["corp"], args["year"])["sections"]
    hits = []
    for s in secs:
        lines = s["text"].splitlines()
        for i, line in enumerate(lines):
            if args["keyword"] in line:
                around = lines[max(0, i - 1) : i + 2]  # 앞뒤 한 줄
                hits.append({"no": s["no"], "title": s["title"], "lines": [x[:300] for x in around]})
    return {"hits": hits[:20], "total": len(hits)}


ctx.report("찾기만", "find_in_report 하나", ctx.run_strategy("찾기만", ["find_in_report"], None))
ctx.report(
    "찾기 + 앞뒤",
    "find_in_report + 앞뒤 한 줄",
    ctx.run_strategy("찾기 + 앞뒤", ["find_in_report"], None, tool_fn=find_with_context),
)
