"""단일 에이전트 vs 순차 팀 vs 병렬 팀 — 같은 질문, 같은 검색 캐시로 시간·토큰·인용을 비교한다 (강의 12편).
사용: python -m dart_rag.compare_team  → data/compare_team.json"""

import json
import re

from . import dart
from .single import run as single
from .team import Team

QS = [
    "카카오의 2025년 영업이익과 주요 사업 부문을 알려줘",
    "삼성전자와 SK하이닉스의 2025년 메모리 사업 실적과 위험 요인을 비교해 줘",
    "현대자동차의 2025년 실적과 최근 관세 관련 뉴스를 같이 정리해 줘",
]


def main():
    team, rows = Team(), []
    for q in QS:
        s = single(q)
        cites = len(re.findall(r"출처", s["answer"]))
        rows.append({"q": q, "mode": "single", "seconds": s["seconds"], "tokens": s["tokens"], "tool_calls": len(s["calls"]),
                     "cited_sentences": cites, "answer": s["answer"]})
        for mode, par in (("team_seq", False), ("team_par", True)):
            r = team.run(q, parallel=par)
            rows.append({"q": q, "mode": mode, "seconds": r.get("seconds"), "tokens": r.get("tokens"), "tool_calls": len(r.get("plan", [])),
                         "quote_ok": r.get("quote_ok"), "green": sum(x["badge"] == "green" for x in r.get("report", [])),
                         "sentences": len(r.get("report", [])), "report": r.get("report"), "timeline": r.get("timeline")})
        for x in rows[-3:]:
            print(f"{x['mode']:9s} {x['seconds']:6}s 토큰 {x['tokens']:6} 작업 {x['tool_calls']:2}  {x.get('quote_ok', '')} {x.get('green', '')}/{x.get('sentences', '')}  | {q[:30]}", flush=True)
    (dart.ROOT / "data" / "compare_team.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
