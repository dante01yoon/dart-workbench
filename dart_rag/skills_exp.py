"""스킬 점진적 노출 (강의 6편).

A. 전부: 스킬 8개 본문을 시스템 프롬프트에 다 넣는다.
B. 점진적: 이름·설명(메타데이터)만 보여 주고, 필요할 때 load_skill(name)로 본문을 읽게 한다.
과제 8개는 각각 스킬 하나가 필요하다. 지표: 출력 표식 준수(스킬을 실제로 따랐나), 맞는 스킬을 읽었나, 총 입력 토큰.
사용: python -m dart_rag.skills_exp → data/skills_exp.json
"""

import json
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from . import dart, harness
from .tools import TOOLS15, run_tool

SKILL_DIR = dart.ROOT / "skills"
SKILLS = {}
for p in sorted(SKILL_DIR.glob("*/SKILL.md")):
    text = p.read_text(encoding="utf-8")
    meta = dict(re.findall(r"^(name|description): (.+)$", text, re.M))
    SKILLS[meta["name"]] = {"description": meta["description"], "body": text,
                            "marker": re.search(r'첫 줄은 "(\[.+?\])"', text).group(1)}

TASKS = [
    ("카카오 2025년 배당이 공시대로 맞는지 점검해 줘", "dividend-check"),
    ("현대자동차 2025년 수익성 분석해 줘", "margin-analysis"),
    ("SK하이닉스 2025년 지배구조 정리해 줘", "shareholder-structure"),
    ("삼성전자 2025년 인력 현황 정리해 줘", "workforce"),
    ("카카오 2025년 감사 관련 위험 신호 있어?", "audit-red-flags"),
    ("삼성전자 2025년 자사주 정책 정리해 줘", "buyback-review"),
    ("SK하이닉스 2025년 임원 보수 정리해 줘", "exec-pay"),
    ("현대자동차 2024년과 2025년 비교표 만들어 줘", "yoy-table"),
]
LOAD = {"type": "function", "function": {"name": "load_skill", "description": "스킬 본문(작업 절차·출력 형식)을 읽는다. 작업에 맞는 스킬이 있으면 먼저 읽어라.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string", "enum": list(SKILLS)}}, "required": ["name"]}}}


def llm(msgs, tools):
    body = {"model": os.environ["FAST_MODEL"], "messages": msgs, "tools": tools, "max_tokens": 2500,
            "reasoning": {"effort": "none"}, "usage": {"include": True}, "parallel_tool_calls": False}
    req = urllib.request.Request(os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=300))
    harness.record(body["model"], r.get("usage", {}), 0)
    return r["choices"][0]["message"], r.get("usage", {})


def run(task, want, mode):
    if mode == "all":
        system = "너는 공시 분석가다. 아래 스킬 중 맞는 것을 골라 그 절차와 출력 형식을 정확히 따르라.\n\n" + \
                 "\n\n".join(s["body"] for s in SKILLS.values())
        tools = TOOLS15
    else:
        system = "너는 공시 분석가다. 사용할 수 있는 스킬(필요하면 load_skill로 본문을 읽어라):\n" + \
                 "\n".join(f"- {n}: {s['description']}" for n, s in SKILLS.items())
        tools = TOOLS15 + [LOAD]
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": task}]
    loaded, total_in = [], 0
    for _ in range(12):
        m, u = llm(msgs, tools)
        total_in += u.get("prompt_tokens", 0)
        msgs.append({k: v for k, v in m.items() if k in ("role", "content", "tool_calls")})
        if not m.get("tool_calls"):
            final = (m.get("content") or "").strip()
            return {"task": task, "mode": mode, "want": want, "loaded": loaded,
                    "follows": final.startswith(SKILLS[want]["marker"]), "prompt_tokens": total_in, "first_line": final.split("\n")[0][:60]}
        for tc in m["tool_calls"]:
            name, args = tc["function"]["name"], json.loads(tc["function"]["arguments"] or "{}")
            if name == "load_skill":
                loaded.append(args.get("name"))
                out = SKILLS.get(args.get("name"), {}).get("body", "그런 스킬은 없다")
            else:
                try:
                    out = json.dumps(run_tool(name, args), ensure_ascii=False)
                except Exception as e:  # noqa: BLE001
                    out = f"오류: {e}"
            msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": out})
    return {"task": task, "mode": mode, "want": want, "loaded": loaded, "follows": False, "prompt_tokens": total_in, "first_line": "턴 상한"}


def main():
    out = []
    for mode in ("all", "progressive"):
        with ThreadPoolExecutor(4) as ex:
            rows = list(ex.map(lambda t: run(t[0], t[1], mode), TASKS))
        out += rows
        n = len(rows)
        print(f"{mode:12s} 지시 준수 {sum(r['follows'] for r in rows)}/{n}  "
              + (f"맞는 스킬 읽음 {sum(r['want'] in r['loaded'] for r in rows)}/{n}  " if mode == "progressive" else "")
              + f"평균 입력 토큰 {sum(r['prompt_tokens'] for r in rows) // n:,}", flush=True)
        for r in rows:
            if not r["follows"]:
                print("   ✗", r["task"], "→", r["first_line"], r["loaded"])
    (dart.ROOT / "data" / "skills_exp.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
