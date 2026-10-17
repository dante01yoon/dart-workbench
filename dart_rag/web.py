"""웹 검색 하나로 감싸기 (강의 12편). 백엔드를 바꿔도 에이전트 코드는 그대로다.

- TAVILY_API_KEY가 있으면 Tavily(search·extract), 없으면 키 없이 ddgs 뉴스 검색 + 직접 본문 추출.
- 같은 질문을 다시 보내면 캐시(data/web_cache.json)에서 꺼낸다 → 전후 비교 실험을 같은 입력으로 돌릴 수 있다.
"""

import hashlib
import html
import json
import os
import re
import urllib.request

from . import dart

CACHE = dart.ROOT / "data" / "web_cache.json"
_cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}


def _cached(key, fn):
    h = hashlib.sha1(key.encode()).hexdigest()[:16]
    if h not in _cache:
        _cache[h] = fn()
        CACHE.write_text(json.dumps(_cache, ensure_ascii=False))
    return _cache[h]


def _post(url, body, key):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def web_search(query, k=5, days=None):
    """[{title, url, date, snippet}]. days를 주면 최근 N일 기사만."""
    key = os.environ.get("TAVILY_API_KEY")

    def run():
        if key:
            r = _post("https://api.tavily.com/search", {"query": query, "max_results": k, "topic": "news", **({"days": days} if days else {})}, key)
            return [{"title": x["title"], "url": x["url"], "date": x.get("published_date", ""), "snippet": x.get("content", "")}
                    for x in r.get("results", [])]
        from ddgs import DDGS

        tl = None if not days else ("d" if days <= 1 else "w" if days <= 7 else "m" if days <= 31 else "y")
        r = DDGS().news(query, max_results=k, region="kr-kr", timelimit=tl)
        return [{"title": x["title"], "url": x["url"], "date": x.get("date", ""), "snippet": x.get("body", "")} for x in r]

    return _cached(f"search|{bool(key)}|{query}|{k}|{days}", run)


def fetch_page(url, limit=6000):
    """기사 본문 텍스트(앞 limit자). 실패하면 빈 문자열."""
    key = os.environ.get("TAVILY_API_KEY")

    def run():
        try:
            if key:
                r = _post("https://api.tavily.com/extract", {"urls": [url]}, key)
                return (r.get("results") or [{}])[0].get("raw_content", "")[:limit]
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
            raw = re.sub(r"<(script|style|nav|header|footer|aside)\b.*?</\1>", " ", raw, flags=re.S | re.I)
            paras = [html.unescape(re.sub(r"<[^>]+>", " ", p)) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", raw, re.S | re.I)]
            text = "\n".join(re.sub(r"\s+", " ", p).strip() for p in paras if len(p.strip()) > 30)
            return text[:limit]
        except Exception:  # noqa: BLE001 — 막힌 사이트는 건너뛴다
            return ""

    return _cached(f"page|{bool(key)}|{url}", run)
