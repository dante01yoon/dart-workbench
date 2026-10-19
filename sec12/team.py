"""12편 공용: 기업 리서치 팀 — 오케스트레이터 · 워커.

planner → [공시 담당 · 재무 담당 · 뉴스 담당] → writer
- 워커는 근거를 {claim, source, quote}로만 넘긴다. quote는 원문에서 그대로 복사한 문장이어야 한다.
- 재무 담당은 LLM 없이 재무 API 숫자를 그대로 근거로 만든다.
- 노력 규칙: 한 회사 단순 질문은 작업 2~3개, 회사 비교는 회사당 2개 안팎, 전체 상한 MAX_TASKS.
- parallel=True면 워커를 동시에, False면 하나씩 돌린다(순차 팀).
"""

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec10"))
from cite import Store, run_tool  # 10편 검색 · 재무 도구 (sec10 → sec07 경로도 함께 잡힌다)
from context import chat
from web import fetch_page, web_search

CORPS = ["삼성전자", "SK하이닉스", "현대자동차", "카카오"]
MAX_TASKS = 8
PLANNER = f"""너는 한국 상장사 리서치 팀의 계획 담당이다. 질문을 작업으로 나눠라.
워커: "filings"(2025년 사업보고서 본문 검색), "financials"(재무 API 숫자: 매출액 · 영업이익 · 당기순이익), "news"(최근 뉴스 검색).
대상 회사: {", ".join(CORPS)}.
노력 규칙: 한 회사 단순 질문은 작업 2~3개, 회사 비교는 회사당 2개 안팎, 전체 {MAX_TASKS}개 이하. 같은 걸 두 번 찾지 마라.
숫자를 묻으면 financials를 꼭 넣는다. 투자 권유를 요구하면 tasks를 비우고 refuse를 true로.
JSON만: {{"refuse": false, "tasks": [{{"worker": "filings", "corp": "삼성전자", "query": "..."}}]}}"""
EXTRACT = """아래 [자료]에서 [과제]에 답하는 근거를 최대 4개 뽑아라.
각 근거: claim(한 문장 요약), src(자료 번호), quote(자료에서 그대로 복사한 30~150자 문장. 바꾸거나 줄이지 마라).
근거가 없으면 빈 목록. JSON만: {"evidence": [{"claim": "...", "src": 1, "quote": "..."}]}"""
WRITER = """너는 리서치 보고서 작성 담당이다. [근거]만 써서 질문에 답하는 짧은 보고서(4~8문장)를 써라.
문장마다 쓴 근거 id를 cites에 넣는다. 금액은 "43조 6,011억 원"처럼 조 · 억 단위로 쓴다.
근거가 부족한 부분은 "확인되지 않음"이라고 쓴다. 투자 권유 금지.
JSON만: {"report": [{"sentence": "...", "cites": ["e1"]}]}"""


def parse(raw):
    """모델 답에서 JSON 덩어리만 꺼낸다. 못 꺼내면 빈 dict."""
    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}


def norm(s):
    return re.sub(r"\s+", "", s or "")


def clean_task(t):
    """모델이 쓴 계획을 그대로 믿지 않는다: 회사 이름 공백 · 별칭을 정리하고, 모르는 회사는 버린다."""
    # 34편: 지시문 v2가 검색어 없는 작업을 내 실행이 멈췄다 → 재무는 검색어가 필요 없고, 검색 작업은 버린다
    if not t.get("query"):
        if t.get("worker") != "financials":
            return None
        t = {**t, "query": ""}
    raw = norm(t.get("corp"))
    corp = next((c for c in CORPS if raw and (c in raw or raw in c)), None)
    return {**t, "corp": corp} if corp or t.get("worker") == "news" else None


class Team:
    def __init__(self, store=None):
        self.store = store or Store()
        self.retries = 0

    def llm(self, system, user, max_tokens=6000):
        """빈 답이면(생각하느라 한도를 다 쓴 경우) 한도를 늘려 한 번 더 부른다. 다시 부른 횟수는 self.retries에 센다."""
        raw, u = chat(f"{system}\n\n{user}", max_tokens=max_tokens)
        cost = float(u.get("cost") or 0)
        if not raw:
            self.retries += 1
            raw, u = chat(f"{system}\n\n{user}", max_tokens=max_tokens * 3)
            cost += float(u.get("cost") or 0)
        return parse(raw), cost

    # ---------- 워커 ----------
    def w_filings(self, t):
        ids = self.store.search(t["query"], t["corp"], k=6)
        docs = [
            {
                "kind": "공시",
                "source": f"{self.store.chunks[i]['corp']} 2025 사업보고서 · {self.store.chunks[i]['section']}",
                "text": self.store.chunks[i]["text"],
            }
            for i in ids
        ]
        return self.extract(t, docs)

    def w_news(self, t):
        docs = []
        for h in web_search(f"{t.get('corp') or ''} {t['query']}".strip())[:3]:
            body = fetch_page(h["url"]) or h["snippet"]
            if body:
                docs.append(
                    {"kind": "뉴스", "source": f"{h['title']} ({h['date'][:16]}) {h['url']}", "text": body}
                )
        return self.extract(t, docs)

    def w_financials(self, t):
        rows = run_tool("key_accounts", {"corp": t["corp"], "year": 2025}).get("rows", [])
        ev, seen = [], set()
        for r in rows:
            name = r["account_nm"].split("(")[0]
            if (
                r["fs_nm"].startswith("연결")
                and name in ("매출액", "영업이익", "당기순이익")
                and name not in seen
            ):
                seen.add(name)
                quote = f"{r['account_nm']} 당기 {r['thstrm_amount']}원 / 전기 {r['frmtrm_amount']}원"
                ev.append(
                    {
                        "claim": f"{t['corp']} 2025년 연결 {r['account_nm']} {r['thstrm_amount']}원(전년 {r['frmtrm_amount']}원)",
                        "source": f"재무 API 주요 계정 · {t['corp']} 2025 연결",
                        "quote": quote,
                        "kind": "재무",
                        "text": quote,
                    }
                )
        return ev, 0.0

    def extract(self, t, docs):
        if not docs:
            return [], 0.0
        blob = "\n\n".join(f"[{n}] {d['source']}\n{d['text'][:2500]}" for n, d in enumerate(docs, 1))
        j, cost = self.llm(EXTRACT, f"[과제] {t.get('corp') or ''} {t['query']}\n\n[자료]\n{blob}")
        ev = []
        for e in j.get("evidence", []):
            n = e.get("src")
            if isinstance(n, int) and 1 <= n <= len(docs):
                d = docs[n - 1]
                ev.append(
                    {
                        "claim": e.get("claim", ""),
                        "source": d["source"],
                        "quote": e.get("quote", ""),
                        "kind": d["kind"],
                        "text": d["text"],
                    }
                )
        return ev, cost

    def run_task(self, t, t0, log):
        start = time.time() - t0
        fn = {"filings": self.w_filings, "news": self.w_news, "financials": self.w_financials}[t["worker"]]
        try:
            ev, cost = fn(t)
        except Exception as e:  # noqa: BLE001 — 워커 하나가 실패해도 팀은 계속한다
            ev, cost, t["error"] = [], 0.0, str(e)[:120]
        log.append(
            {
                "who": t["worker"],
                "corp": t.get("corp"),
                "query": t["query"],
                "start": round(start, 1),
                "end": round(time.time() - t0, 1),
                "n": len(ev),
                "cost": cost,
            }
        )
        return ev

    # ---------- 팀 ----------
    def run(self, question, parallel=True):
        t0, log, self.retries = time.time(), [], 0
        plan, pcost = self.llm(PLANNER, f"질문: {question}")
        log.append({"who": "planner", "start": 0.0, "end": round(time.time() - t0, 1), "n": 0, "cost": pcost})
        if plan.get("refuse"):
            return {
                "question": question,
                "refused": True,
                "report": [],
                "evidence": [],
                "timeline": log,
                "seconds": round(time.time() - t0, 1),
                "cost": pcost,
            }
        tasks = [
            c
            for c in (
                clean_task(t)
                for t in plan.get("tasks", [])
                if t.get("worker") in ("filings", "news", "financials")
            )
            if c
        ]
        tasks = tasks[:MAX_TASKS]
        if parallel:
            with ThreadPoolExecutor(len(tasks) or 1) as ex:
                results = list(ex.map(lambda t: self.run_task(t, t0, log), tasks))
        else:
            results = [self.run_task(t, t0, log) for t in tasks]
        evidence = []
        for ev in results:
            for e in ev:
                e["id"] = f"e{len(evidence) + 1}"
                e["verified"] = len(norm(e["quote"])) >= 10 and norm(e["quote"]) in norm(e["text"])
                evidence.append(e)
        usable = [e for e in evidence if e["verified"]]  # 원문에 없는 인용은 writer에게 넘기지 않는다
        blob = "\n".join(f'{e["id"]} [{e["source"]}] {e["claim"]} — "{e["quote"]}"' for e in usable)
        w0 = time.time() - t0
        rep, wcost = self.llm(WRITER, f"질문: {question}\n\n[근거]\n{blob}", max_tokens=10000)
        log.append(
            {"who": "writer", "start": round(w0, 1), "end": round(time.time() - t0, 1), "n": 0, "cost": wcost}
        )
        ids = {e["id"] for e in usable}
        report = [{**r, "cites": [c for c in r.get("cites", []) if c in ids]} for r in rep.get("report", [])]
        return {
            "question": question,
            "refused": False,
            "tasks": tasks,
            "report": report,
            "evidence": [{k: v for k, v in e.items() if k != "text"} for e in evidence],
            "timeline": log,
            "seconds": round(time.time() - t0, 1),
            "cost": round(sum(x["cost"] for x in log), 4),
            "quote_ok": f"{len(usable)}/{len(evidence)}",
            "retries": self.retries,
        }
