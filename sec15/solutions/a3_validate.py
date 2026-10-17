"""과제 3 풀이: 인자를 스키마로 확인하고, 틀리면 isError로 돌려준다(서버가 죽지도, 엉뚱한 값을 주지도 않게).
없는 회사(LG전자)를 물으면 모델이 오류 문장을 읽고 스스로 "없다"고 답하는지 본다.
사용: 01_talk처럼 직접 부른다 — get_financials(corp="LG전자")를 server.py와 이 파일에 각각 보내 비교한다.
      (Claude Code는 스키마의 enum을 보고 LG전자 질문에 도구를 아예 부르지 않는다.)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server

base = server.call_tool
SCHEMA = {t["name"]: t["inputSchema"] for t in server.TOOLS}


def check(name, args):
    s = SCHEMA[name]
    for key in s.get("required", []):
        if key not in args:
            raise ValueError(f"'{key}' 인자가 필요합니다")
    for key, v in args.items():
        enum = s["properties"].get(key, {}).get("enum")
        if enum and v not in enum:
            raise ValueError(f"{key}={v!r}는 지원하지 않습니다. 가능한 값: {', '.join(map(str, enum))}")


def call_tool(name, args):
    check(name, args)  # 실패하면 server.handle이 isError 결과로 바꾼다
    return base(name, args)


server.call_tool = call_tool

if __name__ == "__main__":
    server.main()
