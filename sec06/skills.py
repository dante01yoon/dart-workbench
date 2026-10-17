"""6편 공용: 스킬 읽기 · 모델 호출 · 에이전트 루프(한 턴에 도구 하나, 5편과 같은 강제)."""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec02"))
from tools15 import ROOT, TOOLS, run_tool

MODEL = os.environ.get("MODEL", "deepseek/deepseek-v4-flash")
TOOL_OF = {}  # 스킬 이름 → 그 스킬이 쓰는 공시 도구
SKILLS = {}
for p in sorted((ROOT / "skills").glob("*/SKILL.md")):
    text = p.read_text(encoding="utf-8")
    meta = dict(re.findall(r"^(name|description): (.+)$", text, re.MULTILINE))
    SKILLS[meta["name"]] = {
        "description": meta["description"],
        "body": text,
        "marker": re.search(r'첫 줄은 "(\[.+?\])"', text).group(1),
    }
    TOOL_OF[meta["name"]] = next(t["function"]["name"] for t in TOOLS if t["function"]["name"] in text)


EXAMPLES = [
    ("삼성전자", 2024),
    ("삼성전자", 2025),
    ("카카오", 2024),
    ("카카오", 2025),
]  # 큰 스킬 부록에 넣을 예시


def appendix(name):
    """큰 스킬: 본문 뒤에 실제 공시 응답 예시(EXAMPLES)를 부록으로 붙인다."""
    parts = []
    for corp, year in EXAMPLES:
        r = run_tool(TOOL_OF[name], {"corp": corp, "year": year})
        parts.append(f"### 예시: {corp} {year} {TOOL_OF[name]}\n{json.dumps(r, ensure_ascii=False)}")
    return "\n\n## 부록: 실제 응답 예시\n" + "\n\n".join(parts)


def body(name, big):
    return SKILLS[name]["body"] + (appendix(name) if big else "")


LOAD_SKILL = {
    "type": "function",
    "function": {
        "name": "load_skill",
        "description": "스킬 본문(작업 절차·출력 형식)을 읽는다. 작업에 맞는 스킬이 있으면 먼저 읽어라.",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string", "enum": list(SKILLS)}},
            "required": ["name"],
        },
    },
}


def llm(messages, tools=None, max_tokens=2500):
    body_ = {"model": MODEL, "messages": messages, "max_tokens": max_tokens, "usage": {"include": True}}
    if tools:
        body_ |= {"tools": tools, "parallel_tool_calls": False}
    req = urllib.request.Request(
        os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions",
        data=json.dumps(body_).encode(),
        headers={
            "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
            "Content-Type": "application/json",
        },
    )
    r = json.load(urllib.request.urlopen(req, timeout=300))
    m = r["choices"][0]["message"]
    if m.get("tool_calls"):  # 5편처럼 한 턴에 도구 하나만 실행한다
        m["tool_calls"] = m["tool_calls"][:1]
    return m, r.get("usage", {})


def loop(system, task, tools, extra=None, max_turns=12, log=None, check=None):
    """에이전트 루프. extra={도구 이름: 함수(args) → 문자열}은 공시 도구가 아닌 도구(load_skill, delegate).
    check(답) → None이면 끝, 문장이면 그 문장을 다시 보내 일을 이어 시킨다(완료 확인)."""
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": task}]
    calls, used = [], []
    for _ in range(max_turns):
        m, u = llm(msgs, tools)
        calls.append({"in": u.get("prompt_tokens", 0), "cost": float(u.get("cost") or 0)})
        msgs.append({k: v for k, v in m.items() if k in ("role", "content", "tool_calls")})
        if not m.get("tool_calls"):
            final = (m.get("content") or "").strip()
            nudge = check(final) if check else None
            if not nudge:
                return final, calls, used
            msgs.append({"role": "user", "content": nudge})
            continue
        for tc in m["tool_calls"]:
            name, args = tc["function"]["name"], json.loads(tc["function"]["arguments"] or "{}")
            used.append((name, args))
            if log:
                log(name, args)
            if extra and name in extra:
                out = extra[name](args)
            else:
                out = json.dumps(run_tool(name, args), ensure_ascii=False)
            msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": out})
    return "(턴 한도)", calls, used
