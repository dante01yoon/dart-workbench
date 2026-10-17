"""12편 ② 단일 에이전트 vs 순차 팀 vs 병렬 팀 — 같은 질문 3개, 같은 검색 · 뉴스 캐시로 시간 · 비용 · 작업 수 · 출처 단 문장을 잰다.
사용: uv run --group frameworks python sec12/02_compare.py → data/team_compare.json"""

import json

from single import run as single
from team import Team
from web import ROOT  # web이 sec10 경로를 잡고 ROOT를 들고 있다

QS = [
    "카카오의 2025년 영업이익과 주요 사업 부문을 알려줘",
    "삼성전자와 SK하이닉스의 2025년 실적과 위험 요인을 비교해 줘",
    "현대자동차의 2025년 실적과 최근 관세 관련 뉴스를 같이 정리해 줘",
]

team, rows = Team(), []
for q in QS:
    s = single(q, team.store)
    rows.append(
        {
            "q": q,
            "mode": "단일",
            "seconds": s["seconds"],
            "cost": s["cost"],
            "work": len(s["calls"]),
            "cited": f"출처 {s['answer'].count('출처')}곳(원문 대조 불가)",  # 글로 적은 출처라 코드로 확인할 수 없다
            "timeline": s["calls"],
            "answer": s["answer"],
        }
    )
    for mode, par in (("순차 팀", False), ("병렬 팀", True)):
        r = team.run(q, parallel=par)
        rows.append(
            {
                "q": q,
                "mode": mode,
                "seconds": r["seconds"],
                "cost": r["cost"],
                "work": len(r.get("tasks", [])),
                "cited": f"{sum(bool(x['cites']) for x in r['report'])}/{len(r['report'])}",
                "quote_ok": r.get("quote_ok"),
                "retries": r.get("retries", 0),
                "timeline": r["timeline"],
                "report": r["report"],
                "evidence": r["evidence"],
            }
        )
    print(f"■ {q}")
    for x in rows[-3:]:
        extra = f"  인용 원문 일치 {x['quote_ok']}" if x.get("quote_ok") else ""
        print(
            f"  {x['mode']:5s} {x['seconds']:6.1f}초  ${x['cost']:.4f}  작업 {x['work']:2d}  출처 단 문장 {x['cited']}{extra}",
            flush=True,
        )
(ROOT / "data" / "team_compare.json").write_text(json.dumps(rows, ensure_ascii=False))
print("저장 → data/team_compare.json   타임라인 화면: uv run python sec12/03_timeline_web.py")
