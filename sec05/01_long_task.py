"""5편 ① 긴 작업에서 컨텍스트 관리하기.

과제: 4개사 × 2개년마다 dividends·key_accounts를 불러(도구 호출 16번) 24칸 표를 채운다.
전략:
  none          아무것도 안 함. 도구 결과가 대화에 계속 쌓인다
  clear         최근 도구 결과 KEEP(3)개만 남기고 오래된 결과는 지운다 + 값을 적어 둘 메모 도구(save_note)
  compact       입력이 THRESHOLD 토큰을 넘으면 지금까지의 기록을 요약해 갈아 끼운다
  compact+todo  compact + 매 턴 "남은 할 일" 목록을 다시 읽어 준다
지표: 맞힌 칸(도구 결과로 직접 계산한 정답과 비교), 턴, 총 입력 토큰, 최대 입력 토큰, 비용 → data/long_task.json
모델: deepseek-v4-flash
사용: uv run python sec05/01_long_task.py [전략 ...]   그래프: uv run python sec05/02_saw.py
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec02"))
from tools15 import ROOT, TOOLS, run_tool

MODEL = os.environ.get("MODEL", "deepseek/deepseek-v4-flash")
CORPS = ["삼성전자", "SK하이닉스", "현대자동차", "카카오"]
YEARS = [2024, 2025]
THRESHOLD = 6_000
KEEP = 3  # clear: 남겨 둘 최근 도구 결과 수
USE_NOTE = True  # clear: 메모 도구(save_note)를 줄지
TASK = (
    "삼성전자, SK하이닉스, 현대자동차, 카카오 4개사의 2024년과 2025년 각각에 대해 "
    "① 보통주 주당 현금배당금(원) ② 연결 현금배당성향(%) ③ 연결 영업이익(원)을 구하라. "
    "회사·연도마다 dividends와 key_accounts 도구를 각각 한 번씩 불러 확인하라(추측 금지). "
    '다 모으면 마지막에 JSON만 출력: {"rows": [{"corp": "삼성전자", "year": 2025, "dps": 1668, '
    '"payout": 30.5, "op": 43601051000000}]}'
)
NOTE_TOOL = {
    "type": "function",
    "function": {
        "name": "save_note",
        "description": "나중에 쓸 값을 메모에 적는다. 오래된 도구 결과는 지워지니 필요한 숫자는 여기 적어 둔다.",
        "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    },
}
WORK_TOOLS = [t for t in TOOLS if t["function"]["name"] in ("dividends", "key_accounts")]


def num(s):
    try:
        return float(str(s).replace(",", "").strip())
    except ValueError:
        return None


def truth():
    """정답: 같은 도구를 우리 코드가 직접 불러 계산한다."""
    out = {}
    for c in CORPS:
        for y in YEARS:
            d = run_tool("dividends", {"corp": c, "year": y})["rows"]
            dps = next(
                num(x["thstrm"])
                for x in d
                if x["se"].startswith("주당 현금배당금") and x["stock_knd"] == "보통주"
            )
            pay = next(num(x["thstrm"]) for x in d if x["se"].startswith("(연결)현금배당성향"))
            k = run_tool("key_accounts", {"corp": c, "year": y})["rows"]
            op = next(
                num(x["thstrm_amount"])
                for x in k
                if x["account_nm"] == "영업이익" and x["fs_nm"] == "연결재무제표"
            )
            out[(c, y)] = {"dps": dps, "payout": pay, "op": op}
    return out


def score(final, gold):
    m = re.search(r"\{.*\}", final, re.DOTALL)
    try:
        rows = json.loads(m.group(0))["rows"] if m else []
    except json.JSONDecodeError:
        rows = []
    got = {(r.get("corp"), int(r.get("year") or 0)): r for r in rows if isinstance(r, dict)}
    ok = 0
    for key, g in gold.items():
        r = got.get(key, {})
        ok += num(r.get("dps")) == g["dps"]
        ok += (
            num(r.get("payout")) is not None
            and g["payout"] is not None
            and abs(num(r.get("payout")) - g["payout"]) < 0.06
        )
        ok += (
            num(r.get("op")) is not None and abs(num(r.get("op")) - g["op"]) < 1_000_000
        )  # 백만 원 반올림 허용
    return ok


def llm(messages, tools=None, max_tokens=3000):
    body = {"model": MODEL, "messages": messages, "max_tokens": max_tokens, "usage": {"include": True}}
    if tools:
        body |= {
            "tools": tools,
            "parallel_tool_calls": False,
        }  # 한 턴에 도구 하나 → 실제 긴 작업처럼 턴이 쌓인다
    req = urllib.request.Request(
        os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
            "Content-Type": "application/json",
        },
    )
    r = json.load(urllib.request.urlopen(req, timeout=300))
    return r["choices"][0]["message"], r.get("usage", {})


def todo_text(done):
    left = [
        f"{c} {y} {t}"
        for c in CORPS
        for y in YEARS
        for t in ("dividends", "key_accounts")
        if (c, y, t) not in done
    ]
    return "남은 할 일: " + (", ".join(left) if left else "없음 — 이제 JSON 표를 출력하라")


def summarize(running, new_part):
    """점진 요약: (이전 요약 + 그 뒤 새 기록)만 요약한다. 기록 전체를 앞에서 자르면 최신 결과가 빠진다."""
    prompt = (
        "에이전트 작업 기록을 요약한다. [이전 요약]과 [새 기록]에서 확인된 값(회사·연도·주당배당금·배당성향·영업이익)과 "
        "이미 부른 도구를 빠짐없이 표로 정리하라. 숫자는 원문 그대로.\n"
        f"[이전 요약]\n{running}\n[새 기록]\n{new_part}"
    )
    m, u = llm([{"role": "user", "content": prompt}], max_tokens=2000)
    return m.get("content") or running, u


def run(strategy, gold, max_turns=45):
    tools = WORK_TOOLS + ([NOTE_TOOL] if strategy == "clear" and USE_NOTE else [])
    msgs = [
        {"role": "system", "content": "너는 공시 데이터 수집 에이전트다. 도구 결과에서 값을 정확히 옮겨라."},
        {"role": "user", "content": TASK},
    ]
    notes, done, curve, cost, running, sum_cost = [], set(), [], 0.0, "(없음)", 0.0
    for turn in range(max_turns):
        send = msgs + ([{"role": "user", "content": todo_text(done)}] if strategy == "compact+todo" else [])
        m, u = llm(send, tools)
        # 모델이 도구를 한꺼번에 여러 개 불러도 첫 번째만 실행한다(Flash는 parallel_tool_calls를 무시했다)
        if m.get("tool_calls"):
            m["tool_calls"] = m["tool_calls"][:1]
        curve.append(u.get("prompt_tokens", 0))
        cost += float(u.get("cost") or 0)
        msgs.append({k: v for k, v in m.items() if k in ("role", "content", "tool_calls")})
        if not m.get("tool_calls"):
            final = m.get("content") or ""
            return {
                "strategy": strategy,
                "cells": score(final, gold),
                "of": 3 * len(gold),
                "turns": turn + 1,
                "total_prompt_tokens": sum(curve),
                "peak_prompt_tokens": max(curve),
                "cost": round(cost, 4),
                "summary_cost": round(sum_cost, 4),
                "curve": curve,
                "final": final[:3000],
            }
        for tc in m["tool_calls"]:
            name, args = tc["function"]["name"], json.loads(tc["function"]["arguments"] or "{}")
            if name == "save_note":
                notes.append(args.get("text", ""))
                out = "저장함"
            else:
                out = json.dumps(run_tool(name, args), ensure_ascii=False)
                done.add((args.get("corp"), int(args.get("year") or 0), name))
            msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": out})
        if strategy == "clear":
            tool_idx = [i for i, x in enumerate(msgs) if x["role"] == "tool" and x["content"] != "저장함"]
            for i in tool_idx[:-KEEP]:
                msgs[i] = {**msgs[i], "content": "[오래된 도구 결과 지움 — 필요한 값은 save_note에 있다]"}
            if notes:
                msgs[0] = {
                    **msgs[0],
                    "content": msgs[0]["content"].split("\n[메모]")[0] + "\n[메모]\n" + "\n".join(notes),
                }
        if strategy.startswith("compact") and curve[-1] > THRESHOLD:
            running, u = summarize(running, json.dumps(msgs[2:], ensure_ascii=False)[-100_000:])
            cost += float(u.get("cost") or 0)
            sum_cost += float(u.get("cost") or 0)
            msgs = msgs[:2] + [
                {
                    "role": "user",
                    "content": "[지금까지 요약 — 여기 있는 값은 이미 도구로 확인한 값이다]\n" + running,
                }
            ]
    return {
        "strategy": strategy,
        "cells": 0,
        "of": 3 * len(gold),
        "turns": max_turns,
        "total_prompt_tokens": sum(curve),
        "peak_prompt_tokens": max(curve),
        "cost": round(cost, 4),
        "curve": curve,
        "note": "턴 상한",
    }


def main(strategies):
    gold = truth()
    out = []
    for s in strategies:
        r = run(s, gold)
        out.append(r)
        print(
            f"{s:13s} 정답 {r['cells']:2d}/{r['of']}  턴 {r['turns']:2d}  총 입력 {r['total_prompt_tokens']:7,d}  "
            f"최대 {r['peak_prompt_tokens']:6,d}  ${r['cost']:.4f}"
            + (f" (요약 호출 ${r['summary_cost']:.4f})" if r.get("summary_cost") else ""),
            flush=True,
        )
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "long_task.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("저장 → data/long_task.json   그래프: uv run python sec05/02_saw.py")


if __name__ == "__main__":
    main(sys.argv[1:] or ["none", "clear", "compact", "compact+todo"])
