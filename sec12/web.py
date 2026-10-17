"""12편 공용: 뉴스 검색(Tavily search · extract)을 함수 하나로 감싼다.

같은 질문을 다시 보내면 캐시(data/web_cache.json)에서 꺼낸다 → 단일 · 순차 · 병렬을 같은 기사로 비교할 수 있다.
"""

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec10"))
from cite import ROOT

CACHE = ROOT / "data" / "web_cache.json"
_cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}


def _cached(key, fn):
    h = hashlib.sha1(key.encode()).hexdigest()[:16]
    if h not in _cache:
        _cache[h] = fn()
        CACHE.write_text(json.dumps(_cache, ensure_ascii=False))
    return _cache[h]


def _post(url, body):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": "Bearer " + os.environ["TAVILY_API_KEY"],
            "Content-Type": "application/json",
        },
    )
    return json.load(urllib.request.urlopen(req, timeout=60))


def web_search(query, k=5, days=180):
    """뉴스 검색 → [{title, url, date, snippet}]. 기본은 최근 180일."""

    def run():
        r = _post(
            "https://api.tavily.com/search", {"query": query, "max_results": k, "topic": "news", "days": days}
        )
        return [
            {
                "title": x["title"],
                "url": x["url"],
                "date": x.get("published_date", ""),
                "snippet": x.get("content", ""),
            }
            for x in r.get("results", [])
        ]

    return _cached(f"search|{query}|{k}|{days}", run)


def fetch_page(url, limit=6000):
    """기사 본문(앞 limit자). 실패하면 빈 문자열."""

    def run():
        try:
            r = _post("https://api.tavily.com/extract", {"urls": [url]})
            return (r.get("results") or [{}])[0].get("raw_content", "")[:limit]
        except Exception:  # noqa: BLE001 — 막힌 사이트는 건너뛴다
            return ""

    return _cached(f"page|{url}", run)
