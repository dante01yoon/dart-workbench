"""기업 리서치 팀 — 오케스트레이터-워커 (강의 12·13편).

planner → [공시 담당 · 재무 담당 · 뉴스 담당] 병렬 → writer → 인용 검증기
- 워커는 근거를 {claim, source, quote}로만 넘긴다. quote는 원문에서 그대로 복사한 문장이어야 한다.
- 검증기는 quote가 실제 원문(공시 청크·기사 본문)에 있는지 문자열로 대조한다(LLM 없음).
- 노력 규칙: 단순 질문은 작업 2~3개, 비교 질문은 회사당 2개, 전체 상한 MAX_TASKS.
사용: python -m dart_rag.team "질문"
"""

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from .answer import chat
from .search import COMPANIES, Searcher, build_vectors, load_chunks
from .web import fetch_page, web_search

MAX_TASKS = 8

PLANNER = f"""너는 한국 상장사 리서치 팀의 계획 담당이다. 질문을 작업으로 나눠라.
워커: "filings"(사업보고서 본문 검색), "financials"(재무 API 숫자: 매출액·영업이익·당기순이익), "news"(뉴스 검색, "days"로 최근 N일 지정 가능, 기본 90).
대상 회사: {', '.join(COMPANIES)} / 공시 연도: 2024, 2025.
노력 규칙: 한 회사 단순 질문은 작업 2~3개, 회사 비교는 회사당 2개 안팎, 전체 {MAX_TASKS}개 이하. 같은 걸 두 번 찾지 마라.
숫자 질문은 financials를 꼭 넣는다. 투자 권유를 요구하면 tasks를 비우고 refuse=true.
JSON만: {{"refuse": false, "tasks": [{{"worker": "filings", "corp": "삼성전자", "year": 2025, "query": "..."}}]}}"""

EXTRACT = """아래 [자료]에서 [과제]에 답하는 근거를 최대 4개 뽑아라.
각 근거: claim(한 문장 요약), src(자료 번호), quote(자료에서 그대로 복사한 30~150자 문장. 바꾸거나 줄이지 마라).
근거가 없으면 빈 목록. JSON만: {"evidence": [{"claim": "...", "src": 1, "quote": "..."}]}"""

WRITER = """너는 리서치 보고서 작성 담당이다. [근거]만 써서 질문에 답하는 짧은 보고서(4~8문장)를 써라.
문장마다 근거 id를 cites에 넣는다. 근거끼리 숫자를 비교·계산했다면 계산식을 문장에 쓴다. 금액은 읽기 쉽게 "43조 6,011억 원"처럼 조·억 단위로 쓴다.
근거가 부족한 부분은 "확인되지 않음"이라고 쓴다. 투자 권유 금지.
JSON만: {"report": [{"sentence": "...", "cites": ["e1"]}]}"""


def clean_task(t):
    """LLM이 쓴 계획을 그대로 믿지 않는다: 회사 이름 공백·별칭, 연도 문자열을 정리한다."""
    corp = (t.get("corp") or "").strip()
    corp = next((c for c in COMPANIES if c.replace(" ", "") in corp.replace(" ", "") or corp.replace(" ", "") in c), None) if corp else None
    try:
        year = int(str(t.get("year") or 2025)[:4])
    except ValueError:
        year = 2025
    return {**t, "corp": corp, "year": year if year in (2024, 2025) else 2025}


def norm(s):
    return re.sub(r"\s+", "", s or "")


class Team:
    def __init__(self):
        chunks = load_chunks()
        self.s = Searcher(chunks, build_vectors(chunks))
        self.log = []  # (워커, 시작, 끝, 토큰)

    def _llm(self, system, user, fast=True, max_tokens=1500):
        raw, u = chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                      max_tokens=max_tokens, model=os.environ["FAST_MODEL"] if fast else None)
        try:
            return json.loads(raw or "{}"), u.get("total_tokens", 0)
        except json.JSONDecodeError:
            return {}, u.get("total_tokens", 0)

    # ---------- 워커 ----------
    def w_filings(self, t):
        ids = self.s.rerank(t["query"], k=6, corp=t.get("corp"), year=t.get("year"))  # 하이브리드 상위 20 → 작은 모델이 재정렬
        docs = [{"kind": "filing", "source": f"{self.s.chunks[i]['corp']} {self.s.chunks[i]['year']} 사업보고서 · {self.s.chunks[i]['section']}",
                 "text": self.s.chunks[i]["text"]} for i in ids]
        return self._extract(t, docs)

    def w_news(self, t):
        hits = web_search(f"{t.get('corp', '')} {t['query']}".strip(), k=5, days=t.get("days") or 90)  # 기본: 최근 90일
        docs = []
        for h in hits[:3]:
            body = fetch_page(h["url"]) or h["snippet"]
            if body:
                docs.append({"kind": "news", "source": f"{h['title']} ({h['date'][:10]}) {h['url']}", "text": body})
        return self._extract(t, docs)

    def w_financials(self, t):
        from mcp_server.manual import call_tool  # 재무 숫자는 LLM을 거치지 않는다

        d = call_tool("get_financials", {"corp": t["corp"], "year": t.get("year") or 2025})
        ev = []
        for acc, v in d["accounts"].items():
            q = f"{acc} 당기 {v['당기']:,}원 / 전기 {v['전기']:,}원"
            ev.append({"claim": f"{d['corp']} {d['year']}년 연결 {acc}은 {v['당기']:,}원(전년 {v['전기']:,}원)",
                       "source": d["source"], "quote": q, "kind": "financials", "text": q})
        return ev, 0

    def _extract(self, t, docs):
        if not docs:
            return [], 0
        blob = "\n\n".join(f"[{n + 1}] {d['source']}\n{d['text'][:2500]}" for n, d in enumerate(docs))
        j, tok = self._llm(EXTRACT, f"[과제] {t.get('corp', '')} {t['query']}\n\n[자료]\n{blob}")
        ev = []
        for e in j.get("evidence", []):
            n = e.get("src")
            if isinstance(n, int) and 0 < n <= len(docs):
                d = docs[n - 1]
                ev.append({"claim": e.get("claim", ""), "source": d["source"], "quote": e.get("quote", ""), "kind": d["kind"], "text": d["text"]})
        return ev, tok

    def _run_task(self, t, t0):
        start = time.time() - t0
        self.emit({"type": "task_start", "id": t["id"], "worker": t["worker"], "corp": t.get("corp"), "query": t.get("query", ""), "t": round(start, 2)})
        fn = {"filings": self.w_filings, "news": self.w_news, "financials": self.w_financials}[t["worker"]]
        try:
            ev, tok = fn(t)
        except Exception as e:  # noqa: BLE001 — 워커 하나가 죽어도 팀은 계속
            ev, tok = [], 0
            t["error"] = str(e)[:200]
        self.log.append({"task": t, "start": round(start, 2), "end": round(time.time() - t0, 2), "tokens": tok, "n": len(ev)})
        self.emit({"type": "task_end", "id": t["id"], "t": round(time.time() - t0, 2), "n": len(ev), "error": t.get("error"),
                   "claims": [e["claim"] for e in ev]})
        return ev

    # ---------- 팀 ----------
    def run(self, question, parallel=True, emit=None):
        """emit(event dict)을 주면 진행 상황을 실시간으로 내보낸다(캡스톤 SSE)."""
        self.emit = emit or (lambda e: None)
        t0 = time.time()
        self.log = []
        self.emit({"type": "planning", "t": 0})
        plan, ptok = self._llm(PLANNER, question, fast=False, max_tokens=3000)
        if plan.get("refuse"):
            r = {"question": question, "refused": True, "report": [], "evidence": [], "timeline": [], "tokens": ptok}
            self.emit({"type": "done", **r})
            return r
        tasks = [clean_task(t) for t in plan.get("tasks", []) if t.get("worker") in ("filings", "news", "financials")][:MAX_TASKS]
        for n, t in enumerate(tasks):
            t["id"] = f"t{n + 1}"
        self.emit({"type": "plan", "t": round(time.time() - t0, 2), "tasks": tasks})
        if parallel:
            with ThreadPoolExecutor(len(tasks) or 1) as ex:
                results = list(ex.map(lambda t: self._run_task(t, t0), tasks))
        else:
            results = [self._run_task(t, t0) for t in tasks]
        evidence = []
        for ev in results:
            for e in ev:
                e["id"] = f"e{len(evidence) + 1}"
                e["verified"] = len(norm(e["quote"])) >= 10 and norm(e["quote"]) in norm(e["text"])
                evidence.append(e)
        usable = [e for e in evidence if e["verified"]]
        blob = "\n".join(f"{e['id']} [{e['source']}] {e['claim']} — \"{e['quote']}\"" for e in usable)
        w_start = time.time() - t0
        self.emit({"type": "writing", "t": round(w_start, 2), "evidence": len(evidence), "verified": len(usable)})
        for _ in range(2):  # 근거가 많으면 추론 모델이 토큰 상한에 걸려 빈 보고서가 나온 적이 있다 → 넉넉히, 비면 한 번 더
            rep, wtok = self._llm(WRITER, f"질문: {question}\n\n[근거]\n{blob}", fast=False, max_tokens=10000)
            if rep.get("report"):
                break
        self.log.append({"task": {"worker": "writer"}, "start": round(w_start, 2), "end": round(time.time() - t0, 2), "tokens": wtok, "n": 0})
        ids = {e["id"] for e in usable}
        report = []
        for r in rep.get("report", []):
            cites = [c for c in r.get("cites", []) if c in ids]
            report.append({**r, "cites": cites, "badge": "green" if cites else "red"})
        result = {
            "question": question, "refused": False, "plan": tasks, "report": report,
            "evidence": [{k: v for k, v in e.items() if k != "text"} for e in evidence],
            "timeline": self.log, "seconds": round(time.time() - t0, 1),
            "tokens": ptok + wtok + sum(x["tokens"] for x in self.log if x["task"].get("worker") != "writer"),
            "quote_ok": f"{len(usable)}/{len(evidence)}",
        }
        self.emit({"type": "done", **result})
        return result


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "삼성전자와 SK하이닉스의 2025년 메모리 사업 실적과 위험 요인을 비교해 줘"
    r = Team().run(q)
    out = os.path.join(os.path.dirname(__file__), "..", "data", "team_last.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
    for t in r.get("timeline", []):
        print(f"  {t['start']:6.1f}→{t['end']:6.1f}s  {t['task'].get('worker'):10s} {t['task'].get('corp', '')} {t['task'].get('query', '')[:40]}  근거 {t['n']}")
    print("인용 검증:", r.get("quote_ok"), " 토큰:", r.get("tokens"), " 시간:", r.get("seconds"), "s")
    for s in r.get("report", []):
        print(("🟢" if s["badge"] == "green" else "🔴"), s["sentence"], s["cites"])
