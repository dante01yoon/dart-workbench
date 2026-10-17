"""6편 ① 스킬 점진적 노출.

전부      스킬 8개 본문을 시스템 프롬프트에 다 넣는다.
점진적    이름·설명(메타데이터)만 보여 주고, 필요할 때 load_skill(이름)로 본문을 읽게 한다.
작은/큰   큰 스킬은 본문 뒤에 실제 공시 응답 예시(부록)를 붙인 것(8개 합계 약 6만 자).
과제 8개는 각각 스킬 하나가 필요하다. 지표: 출력 표식 준수(스킬을 따랐나), 맞는 스킬을 읽었나, 과제당 입력 토큰, 비용
사용: uv run python sec06/01_skills.py → data/skills_runs.json
"""

import json
from concurrent.futures import ThreadPoolExecutor

from skills import LOAD_SKILL, ROOT, SKILLS, TOOLS, body, loop

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
SETTINGS = [("all", False), ("progressive", False), ("all", True), ("progressive", True)]
LABEL = {"all": "전부", "progressive": "점진적"}


def run(task, want, mode, big):
    if mode == "all":
        system = (
            "너는 공시 분석가다. 아래 스킬 중 맞는 것을 골라 그 절차와 출력 형식을 정확히 따르라.\n\n"
            + "\n\n".join(body(n, big) for n in SKILLS)
        )
        tools, extra = TOOLS, None
    else:
        system = (
            "너는 공시 분석가다. 사용할 수 있는 스킬(필요하면 load_skill로 본문을 읽어라):\n"
            + "\n".join(f"- {n}: {s['description']}" for n, s in SKILLS.items())
        )
        tools, extra = (
            TOOLS + [LOAD_SKILL],
            {
                "load_skill": lambda a: (
                    body(a.get("name"), big) if a.get("name") in SKILLS else "그런 스킬은 없다"
                )
            },
        )
    final, calls, used = loop(system, task, tools, extra)
    loaded = [a.get("name") for n, a in used if n == "load_skill"]
    return {
        "task": task,
        "want": want,
        "mode": mode,
        "big": big,
        "follows": final.split("\n")[0]
        .replace("*", "")
        .strip()
        .startswith(SKILLS[want]["marker"]),  # **굵게**는 봐준다
        "loaded_right": want in loaded,
        "prompt_tokens": sum(c["in"] for c in calls),
        "calls": [c["in"] for c in calls],
        "cost": sum(c["cost"] for c in calls),
        "first_line": final.split("\n")[0][:60],
    }


def main():
    out = []
    for mode, big in SETTINGS:
        with ThreadPoolExecutor(4) as ex:
            rows = list(
                ex.map(
                    run, [t for t, _ in TASKS], [w for _, w in TASKS], [mode] * len(TASKS), [big] * len(TASKS)
                )
            )
        out += rows
        n = len(rows)
        print(
            f"{'큰' if big else '작은'} 스킬 · {LABEL[mode]:3s}  지시 준수 {sum(r['follows'] for r in rows)}/{n}  "
            + (
                f"맞는 스킬 읽음 {sum(r['loaded_right'] for r in rows)}/{n}  "
                if mode == "progressive"
                else ""
            )
            + f"과제당 입력 {sum(r['prompt_tokens'] for r in rows) // n:,}토큰  ${sum(r['cost'] for r in rows):.4f}",
            flush=True,
        )
        for r in rows:
            if not r["follows"]:
                print("    ✗", r["task"], "→", r["first_line"])
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "skills_runs.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("저장 → data/skills_runs.json")


if __name__ == "__main__":
    main()
