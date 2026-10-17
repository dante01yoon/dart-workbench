"""과제 1 풀이: 도구를 하나 더 붙인다 — company_info(기업 개황: 대표이사 · 설립일 · 주소).
서버 코드는 그대로 두고 도구 목록과 call_tool만 넓힌다. Claude Code 설정은 solutions/mcp_a1.json.
사용: claude --strict-mcp-config --mcp-config sec15/solutions/mcp_a1.json --tools "" -p "카카오 대표이사가 누구야?"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server
from tools15 import run_tool

server.TOOLS.append(
    {
        "name": "company_info",
        "description": "기업 개황: 정식 회사명, 대표이사, 설립일, 본사 주소, 결산월.",
        "inputSchema": {
            "type": "object",
            "properties": {"corp": {"type": "string", "enum": server.CORPS}},
            "required": ["corp"],
        },
        "annotations": {"readOnlyHint": True},
    }
)
base = server.call_tool


def call_tool(name, args):
    if name == "company_info":
        return run_tool("company_info", {"corp": args["corp"]})
    return base(name, args)


server.call_tool = call_tool

if __name__ == "__main__":
    server.main()
