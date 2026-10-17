"""긴 작업에서 컨텍스트 관리하기 (강의 5편).

과제: 4개사 × 2개년마다 dividends·key_accounts 도구를 불러(도구 호출 16번 이상) 24칸짜리 표를 채운다.
전략:
  none      아무것도 안 함(도구 결과가 계속 쌓임)
  clear     최근 도구 결과 3개만 남기고 오래된 결과는 지움 + 메모 도구(save_note)
  compact   입력이 THRESHOLD 토큰을 넘으면 지금까지의 대화를 작은 모델이 요약해 갈아 끼움
  compact+todo  compact + 매 턴 "남은 할 일" 목록을 다시 읽어 줌
지표: 정답 칸 수(재무 API로 계산한 정답과 비교), 총 입력 토큰, 최대 입력 토큰(톱니 그래프), 비용, 턴 수
사용: python -m dart_rag.long_task [전략 ...] → data/long_task.json
"""

import json
import os
import re
import sys
import urllib.request

from . import dart, harness
from .answer import chat
from .tools import TOOLS15, run_tool

CORPS = ["삼성전자", "SK하이닉스", "현대자동차", "카카오"]
YEARS = [2024, 2025]
THRESHOLD = 25_000
TASK = ("삼성전자, SK하이닉스, 현대자동차, 카카오 4개사의 2024년과 2025년 각각에 대해 "
        "① 보통주 주당 현금배당금(원) ② 연결 현금배당성향(%) ③ 연결 영업이익(원)을 구하라. "
        "회사·연도마다 dividends와 key_accounts 도구를 각각 한 번씩 불러 확인하라(추측 금지). "
        "다 모으면 마지막에 JSON만 출력: {\"rows\": [{\"corp\": \"삼성전자\", \"year\": 2025, \"dps\": 1668, \"payout\": 30.5, \"op\": 43601051000000}]}")
NOTE_TOOL = {"type": "function", "function": {"name": "save_note", "description": "나중에 쓸 값을 메모에 저장한다(오래된 도구 결과는 지워진다).",
             "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}}
TOOLS = [t for t in TOOLS15 if t["function"]["name"] in ("dividends", "key_accounts")]


def num(s):
    s = str(s).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def truth():
    out = {}
    for c in CORPS:
        for y in YEARS:
            d = run_tool("dividends", {"corp": c, "year": y})["list"]
            dps = next(num(x["thstrm"]) for x in d if x["se"].startswith("주당 현금배당금") and x["stock_knd"] == "보통주")
            pay = next(num(x["thstrm"]) for x in d if x["se"].startswith("(연결)현금배당성향"))
            k = run_tool("key_accounts", {"corp": c, "year": y})["list"]
            op = next(num(x["thstrm_amount"]) for x in k if x["account_nm"].startswith("영업이익") and x["fs_div"] == "CFS")
            out[(c, y)] = {"dps": dps, "payout": pay, "op": op}
    return out


def score(final, gold):
    try:
        rows = json.loads(re.search(r"\{.*\}", final, re.S).group(0))["rows"]
    except Exception:  # noqa: BLE001
        return 0
    got = {(r.get("corp"), int(r.get("year", 0))): r for r in rows}
    ok = 0
    for key, g in gold.items():
        r = got.get(key, {})
        ok += num(r.get("dps")) == g["dps"]
        ok += num(r.get("payout")) is not None and g["payout"] is not None and abs(num(r.get("payout")) - g["payout"]) < 0.06
        ok += num(r.get("op")) is not None and abs(num(r.get("op")) - g["op"]) < 1_000_000  # 백만원 반올림 허용
    return ok


def llm(messages, tools):
    body = {"model": os.environ["FAST_MODEL"], "messages": messages, "tools": tools, "max_tokens": 3000,
            "reasoning": {"effort": "none"}, "usage": {"include": True},
            "parallel_tool_calls": False}  # 한 턴에 도구 하나 — 실제 긴 작업처럼 턴이 쌓이게
    req = urllib.request.Request(os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=300))
    harness.record(body["model"], r.get("usage", {}), 0)
    return r["choices"][0]["message"], r.get("usage", {})


def todo_text(done):
    left = [f"{c} {y} {t}" for c in CORPS for y in YEARS for t in ("dividends", "key_accounts") if (c, y, t) not in done]
    return "남은 할 일: " + (", ".join(left) if left else "없음 — 이제 JSON 표를 출력하라")


def run(strategy, gold, max_turns=45):
    tools = TOOLS + ([NOTE_TOOL] if strategy == "clear" else [])
    msgs = [{"role": "system", "content": "너는 공시 데이터 수집 에이전트다. 도구 결과에서 값을 정확히 옮겨라."},
            {"role": "user", "content": TASK}]
    notes, done, curve, cost, total_in, running = [], set(), [], 0.0, 0, "(없음)"
    for turn in range(max_turns):
        send = list(msgs)
        if strategy == "compact+todo":
            send.append({"role": "user", "content": todo_text(done)})
        m, u = llm(send, tools)
        curve.append(u.get("prompt_tokens", 0))
        total_in += u.get("prompt_tokens", 0)
        cost += float(u.get("cost") or 0)
        msgs.append({k: v for k, v in m.items() if k in ("role", "content", "tool_calls")})
        if not m.get("tool_calls"):
            return {"strategy": strategy, "cells": score(m.get("content") or "", gold), "of": 3 * len(gold), "turns": turn + 1,
                    "total_prompt_tokens": total_in, "peak_prompt_tokens": max(curve), "cost": round(cost, 4), "curve": curve, "final": (m.get("content") or "")[:3000],
                    "calls": sorted(f"{c} {y} {t}" for c, y, t in done)}
        for tc in m["tool_calls"]:
            name, args = tc["function"]["name"], json.loads(tc["function"]["arguments"] or "{}")
            if name == "save_note":
                notes.append(args.get("text", ""))
                out = "저장함"
            else:
                try:
                    out = json.dumps(run_tool(name, args), ensure_ascii=False)
                    done.add((args.get("corp"), int(args.get("year", 0)), name))
                except Exception as e:  # noqa: BLE001
                    out = f"오류: {e}"
            msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": out})
        if strategy == "clear":
            tool_idx = [i for i, x in enumerate(msgs) if x["role"] == "tool" and x["content"] != "저장함"]
            for i in tool_idx[:-3]:
                msgs[i] = {**msgs[i], "content": "[오래된 도구 결과 지움 — 필요한 값은 save_note로 저장해 두었어야 한다]"}
            if notes:
                msgs[0] = {**msgs[0], "content": msgs[0]["content"].split("\n[메모]")[0] + "\n[메모]\n" + "\n".join(notes)}
        if strategy.startswith("compact") and curve[-1] > THRESHOLD:
            # 점진 요약: (이전 요약 + 그 뒤 새 기록)만 요약한다. 처음 버전은 기록 전체를 앞에서 12만 자로 잘라
            # 최신 결과가 빠졌고, 에이전트가 "값이 없다"며 표를 못 냈다(0/24) → 5편 실패 사례.
            new_part = json.dumps(msgs[2:], ensure_ascii=False)
            summary, _ = chat([{"role": "user", "content": "에이전트 작업 기록을 요약한다. [이전 요약]과 [새 기록]에서 확인된 값"
                                                           "(회사·연도·주당배당금·배당성향·영업이익)과 이미 부른 도구를 빠짐없이 표로 정리하라. 숫자는 원문 그대로.\n"
                                                           f"[이전 요약]\n{running}\n[새 기록]\n{new_part[-100_000:]}"}],
                              max_tokens=2000, model=os.environ["FAST_MODEL"], json_mode=False)
            running = summary or running
            msgs = msgs[:2] + [{"role": "user", "content": "[지금까지 요약 — 여기 있는 값은 이미 도구로 확인한 값이다]\n" + running}]
    return {"strategy": strategy, "cells": 0, "of": 3 * len(gold), "turns": max_turns, "total_prompt_tokens": total_in,
            "peak_prompt_tokens": max(curve), "cost": round(cost, 4), "curve": curve, "note": "턴 상한"}


def main(strategies):
    gold = truth()
    out = []
    for s in strategies:
        r = run(s, gold)
        out.append(r)
        print(f"{s:13s} 정답 {r['cells']:2d}/{r['of']}  턴 {r['turns']:2d}  총 입력 {r['total_prompt_tokens']:7,d}  "
              f"최대 {r['peak_prompt_tokens']:6,d}  ${r['cost']:.4f}", flush=True)
    (dart.ROOT / "data" / "long_task.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:] or ["none", "clear", "compact", "compact+todo"])
