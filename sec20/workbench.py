"""20편 공용: 워크벤치 리서치 — 12편 팀 + 16편 MCP 도구 + 13편 심판(반성 루프) + 비용 상한. 진행을 이벤트로 내보낸다.

이벤트(emit에 dict로): planning → plan → task_start / task_end … → writing → verify → (revise → verify 또는 revise_kept) → done
비용이 상한을 넘으면 budget 이벤트를 내고 멈춘다. 투자 권유 질문은 refused.
"""

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sec13"))
sys.path.insert(0, str(HERE.parent / "sec12"))
import verify  # 13편 심판
from team import MAX_TASKS, PLANNER, WRITER, Team, clean_task, norm  # 12편 팀

REVISE = """[보고서]의 일부 문장이 근거로 뒷받침되지 않는다는 판정을 받았다([판정]).
그 문장은 근거가 말하는 만큼만 남기도록 고치거나 지워라. 다른 문장은 그대로 둔다. 새 사실을 지어내지 마라.
문장마다 쓴 근거 id를 cites에 넣는다. JSON만: {"report": [{"sentence": "...", "cites": ["e1"]}]}"""


def clean(rep, ids):
    """작성 담당의 답에서 문장만 남긴다: 문장이 빈 항목은 버리고, 없는 근거 id는 지운다."""
    return [
        {**r, "cites": [c for c in r.get("cites", []) if c in ids]}
        for r in rep.get("report", [])
        if isinstance(r, dict) and r.get("sentence")
    ]


class BudgetExceeded(Exception):
    pass


class Workbench(Team):
    def __init__(self, mcp, emit, cap=0.05):
        super().__init__(store=object())  # 검색은 MCP 서버가 한다 → 로컬 검색기를 싣지 않는다
        self.mcp, self.emit, self.cap, self.spent = mcp, emit, cap, 0.0

    # ---------- 비용 상한 ----------
    def charge(self, cost):
        self.spent += cost
        if self.spent > self.cap:
            raise BudgetExceeded(f"${self.spent:.4f} > 상한 ${self.cap}")

    def llm(self, system, user, max_tokens=6000):
        if self.spent > self.cap:
            raise BudgetExceeded(f"${self.spent:.4f} > 상한 ${self.cap}")
        out, cost = super().llm(system, user, max_tokens)
        self.charge(cost)
        return out, cost

    # ---------- 워커: 공시 · 재무는 MCP 서버의 도구로 ----------
    def w_filings(self, t):
        hits = self.mcp.call("search_filings", {"query": t["query"], "corp": t.get("corp"), "k": 6})
        docs = [
            {"kind": "공시", "source": f"{h['corp']} 2025 사업보고서 · {h['section']}", "text": h["text"]}
            for h in (hits if isinstance(hits, list) else [hits])
        ]
        return self.extract(t, docs)

    def w_financials(self, t):
        fin = self.mcp.call("get_financials", {"corp": t["corp"]})
        ev = []
        for acc, v in fin["accounts"].items():
            quote = f"{acc} 당기 {v['당기']}원 / 전기 {v['전기']}원"
            claim = f"{t['corp']} 2025년 연결 {acc} {v['당기']}원(전년 {v['전기']}원)"
            ev.append(
                {
                    "claim": claim,
                    "source": f"재무 API · {t['corp']} 2025 연결",
                    "quote": quote,
                    "kind": "재무",
                    "text": quote,
                }
            )
        return ev, 0.0

    def run_task(self, t, t0, log):
        self.emit(
            {
                "type": "task_start",
                "id": t["id"],
                "worker": t["worker"],
                "corp": t.get("corp"),
                "query": t["query"],
                "t": round(time.time() - t0, 1),
            }
        )
        ev = super().run_task(t, t0, log)
        self.emit(
            {
                "type": "task_end",
                "id": t["id"],
                "n": len(ev),
                "t": round(time.time() - t0, 1),
                "error": t.get("error"),
                "spent": round(self.spent, 4),
            }
        )
        return ev

    # ---------- 심판 · 반성 ----------
    def check(self, report, evidence):
        judged = verify.badge_sentences(report, evidence)
        self.charge(sum(s["cost"] for s in judged))
        return judged

    def research(self, question, reflect=True):
        t0, log = time.time(), []
        self.emit({"type": "planning", "t": 0.0})
        plan, _ = self.llm(PLANNER, f"질문: {question}")
        if plan.get("refuse"):
            self.emit({"type": "refused", "t": round(time.time() - t0, 1)})
            return {"refused": True, "report": [], "spent": self.spent}
        tasks = [
            c
            for c in (
                clean_task(t)
                for t in plan.get("tasks", [])
                if t.get("worker") in ("filings", "news", "financials")
            )
            if c
        ][:MAX_TASKS]
        tasks = [{**t, "id": f"t{n}"} for n, t in enumerate(tasks, 1)]
        self.emit(
            {"type": "plan", "tasks": tasks, "t": round(time.time() - t0, 1), "spent": round(self.spent, 4)}
        )
        with ThreadPoolExecutor(len(tasks) or 1) as ex:
            results = list(ex.map(lambda t: self.run_task(t, t0, log), tasks))
        evidence = []
        for ev in results:
            for e in ev:
                e["id"] = f"e{len(evidence) + 1}"
                e["verified"] = len(norm(e["quote"])) >= 10 and norm(e["quote"]) in norm(e["text"])
                evidence.append(e)
        usable = [e for e in evidence if e["verified"]]
        blob = "\n".join(f'{e["id"]} [{e["source"]}] {e["claim"]} — "{e["quote"]}"' for e in usable)
        self.emit({"type": "writing", "evidence": len(usable), "t": round(time.time() - t0, 1)})
        rep, _ = self.llm(WRITER, f"질문: {question}\n\n[근거]\n{blob}", max_tokens=10000)
        ids = {e["id"] for e in usable}
        report = clean(rep, ids)
        judged = self.check(report, usable)
        bad = [s for s in judged if s["badge"] != "지지"]
        self.emit(
            {
                "type": "verify",
                "round": 1,
                "ok": len(judged) - len(bad),
                "total": len(judged),
                "t": round(time.time() - t0, 1),
                "spent": round(self.spent, 4),
            }
        )
        rounds = 1
        if reflect and bad:
            note = "\n".join(f'- "{s["sentence"]}" → {s["badge"]}: {s["reason"]}' for s in bad)
            old = "\n".join(f"{s['sentence']} {s['cites']}" for s in report)
            self.emit({"type": "revise", "bad": len(bad), "t": round(time.time() - t0, 1)})
            rep, _ = self.llm(
                REVISE, f"[근거]\n{blob}\n\n[보고서]\n{old}\n\n[판정]\n{note}", max_tokens=10000
            )
            revised = clean(rep, ids)
            if not revised:  # 고친 답이 비면(JSON 깨짐 · 전부 지움) 원래 보고서를 지킨다
                self.emit({"type": "revise_kept", "t": round(time.time() - t0, 1)})
            else:
                judged = self.check(revised, usable)
                bad = [s for s in judged if s["badge"] != "지지"]
                rounds = 2
                self.emit(
                    {
                        "type": "verify",
                        "round": 2,
                        "ok": len(judged) - len(bad),
                        "total": len(judged),
                        "t": round(time.time() - t0, 1),
                        "spent": round(self.spent, 4),
                    }
                )
        out = {
            "refused": False,
            "report": [{k: s[k] for k in ("sentence", "cites", "badge", "reason")} for s in judged],
            "evidence": [{k: e[k] for k in ("id", "source", "claim", "quote")} for e in usable],
            "rounds": rounds - 1,  # 반성(고쳐 쓰기) 횟수
            "seconds": round(time.time() - t0, 1),
            "spent": round(self.spent, 4),
        }
        self.emit({"type": "done", **out, "t": out["seconds"]})
        return out
