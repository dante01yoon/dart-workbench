"""4편 사업보고서 원문 도구. 같은 원문을 세 가지 방식으로 건넨다.

- read_full_report: 원문 전체(수십만 자)를 한 번에
- list_sections + read_section: 목차를 보고 필요한 섹션만. CAP을 정하면 한 번에 CAP자까지만 주고 다음 위치를 알려 준다
- find_in_report: 키워드가 나온 줄만 (최대 20줄)
"""

import sys
from pathlib import Path

from pydantic import BaseModel, ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec02"))
from report import load
from tools15 import Corp, Year, _tool

CAP = None  # read_section 한 번에 돌려줄 최대 글자 수. None이면 섹션 전체


class CorpYear(BaseModel):
    corp: Corp
    year: Year


class Section(CorpYear):
    no: int
    start: int = 0


class Find(CorpYear):
    keyword: str


SPEC = {
    "read_full_report": (CorpYear, "사업보고서 원문 전체를 한 번에 돌려준다."),
    "list_sections": (CorpYear, "사업보고서 목차: 섹션 번호·제목·글자 수. 원문을 읽기 전에 먼저 본다."),
    "read_section": (
        Section,
        (
            "사업보고서의 섹션 하나를 읽는다. no는 list_sections의 번호. "
            "결과에 next_start가 있으면 start에 넣어 이어서 읽는다."
        ),
    ),
    "find_in_report": (
        Find,
        "사업보고서에서 키워드가 나온 줄을 섹션 번호와 함께 최대 20줄 돌려준다(예: '연구개발비').",
    ),
}


def tools(*names):
    return [_tool(n, SPEC[n][0], SPEC[n][1]) for n in names]


def run_tool(name, args):
    if name not in SPEC:
        return {"error": f"'{name}' 도구는 없습니다"}
    try:
        a = SPEC[name][0](**args)
    except ValidationError as e:
        return {"error": "인자가 잘못됐습니다", "details": [x["msg"] for x in e.errors()]}
    secs = load(a.corp, a.year)["sections"]
    if name == "read_full_report":
        return {"text": "\n\n".join(f"[{s['no']}] {s['title']}\n{s['text']}" for s in secs)}
    if name == "list_sections":
        return {"sections": [{"no": s["no"], "title": s["title"], "chars": len(s["text"])} for s in secs]}
    if name == "read_section":
        s = next((s for s in secs if s["no"] == a.no), None)
        if s is None:
            return {"error": f"{a.no}번 섹션이 없습니다. list_sections로 번호를 확인하세요."}
        end = len(s["text"]) if CAP is None else min(len(s["text"]), a.start + CAP)
        out = {"title": s["title"], "total_chars": len(s["text"]), "text": s["text"][a.start : end]}
        if end < len(s["text"]):
            out["next_start"] = end
        return out
    hits = [
        {"no": s["no"], "title": s["title"], "line": line[:300]}
        for s in secs
        for line in s["text"].splitlines()
        if a.keyword in line
    ]
    return {"hits": hits[:20], "total": len(hits)}
