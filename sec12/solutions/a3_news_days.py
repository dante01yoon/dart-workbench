"""과제 3 풀이: 뉴스 담당의 검색 기간을 30일 · 180일 · 365일로 바꾸면 기사 날짜와 근거가 어떻게 달라질까?
사용: uv run --group frameworks python sec12/solutions/a3_news_days.py"""

import _lab  # noqa: F401
import team as T
import web

tm = T.Team()
task = {"worker": "news", "corp": "현대자동차", "query": "관세 영향"}
for days in (30, 180, 365):
    T.web_search = lambda q, days=days: web.web_search(q, days=days)  # 워커가 부르는 검색만 기간을 바꾼다
    hits = web.web_search(f"{task['corp']} {task['query']}", days=days)
    ev, _ = tm.w_news(task)
    print(f"{days:3d}일  기사 날짜: {', '.join(h['date'][5:16] for h in hits[:3])}  · 근거 {len(ev)}개")
    for e in ev[:2]:
        print(f"      {e['claim'][:70]}")
