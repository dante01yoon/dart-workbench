"""3편 ① 도구가 3개 → 15개 → 40개로 늘면 무엇이 변하나. 그리고 40개 중 5개만 보여 주는 도구 검색.
질문 20개(2편과 같은 질문)마다 모델이 맞는 도구를 첫 번에 고르는지, 호출 한 번에 입력 토큰이 얼마인지 잰다.
작은 모델은 결과가 흔들리므로 3번 돌려 평균을 낸다.
사용: uv run python sec03/01_count.py [모델 ...]   → data/tool_count.json, 그래프는 sec03/04_graph.py
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor

from select_lab import REPEAT, SEARCH, Q, pick
from tools40 import ROOT, TOOLS3, TOOLS15, TOOLS40

MODELS = sys.argv[1:] or ["qwen/qwen3.5-9b", "anthropic/claude-haiku-5.5"]
CONFIGS = [
    ("3개", lambda q: TOOLS3),
    ("15개", lambda q: TOOLS15),
    ("40개 (미끼 22개)", lambda q: TOOLS40),
    ("40개 + 도구 검색 5개", lambda q: SEARCH.search(q, 5)),
]

out = []
for model in MODELS:
    print(f"\n■ {model}")
    for label, shown in CONFIGS:
        names = {t["function"]["name"] for t in (TOOLS3 if label == "3개" else TOOLS40)}
        qs = [(q, w) for q, w in Q if w in names] * REPEAT
        with ThreadPoolExecutor(8) as ex:
            res = list(ex.map(lambda x, f=shown, m=model: pick(m, f(x[0]), x[0]), qs))
        ok = sum(g == w for (g, _, _), (_, w) in zip(res, qs))
        row = {
            "model": model.split("/")[-1],
            "config": label,
            "n": len(qs) // REPEAT,
            "accuracy": round(ok / len(qs), 3),
            "prompt_tokens": round(sum(p for _, p, _ in res) / len(qs)),
            "cost_per_call": round(sum(c for _, _, c in res) / len(qs), 6),
            "misses": sorted({(q, g) for (g, _, _), (q, w) in zip(res, qs) if g != w}),
        }
        if label.startswith("40개 + "):
            row["search_recall"] = round(
                sum(w in {t["function"]["name"] for t in SEARCH.search(q, 5)} for q, w in Q) / len(Q), 3
            )
        out.append(row)
        print(
            f"  {label:16s} 정확도 {row['accuracy']:.2f}  입력 토큰 {row['prompt_tokens']:5d}  호출당 ${row['cost_per_call']:.5f}"
            + (f"  검색에 정답 도구가 든 비율 {row['search_recall']:.2f}" if "search_recall" in row else "")
        )
        for q, g in row["misses"]:
            print(f"      ✗ {q} → {g}")

(ROOT / "data").mkdir(exist_ok=True)
(ROOT / "data" / "tool_count.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print("\n저장 → data/tool_count.json   그래프: uv run python sec03/04_graph.py")
