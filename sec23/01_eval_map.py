"""23편 ① 평가 대상 지도 — 우리 DART 리서치 에이전트에서 무엇을 재야 하는지 7면으로 나누고,
지금까지 남긴 실행 기록(1~22편)에서 이미 잰 숫자와 아직 비어 있는 칸을 찾는다. API를 부르지 않는다.
사용: uv run python sec23/01_eval_map.py → 터미널 표 + http://127.0.0.1:8823
"""

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from page import page, serve

QS = {json.loads(line)["id"]: json.loads(line) for line in (ROOT / "eval" / "questions.jsonl").open()}


def load(name):
    return json.loads((DATA / name).read_text())


def build():
    now = load("final_eval.json")["now"]  # 22편 최종 성적표: 같은 20문항 · 워크벤치
    ans = [x for x in now if QS[x["id"]]["type"] not in ("none", "refuse")]
    ref = [x for x in now if QS[x["id"]]["type"] in ("none", "refuse")]
    sent = sum(x["sentences"] for x in now)
    tools = [
        x for x in load("cc_tool_count.json") if x["n"] == 40 and x["search"]
    ]  # 16편: 도구 40개 + 도구 검색
    rag = next(
        r
        for r in load("rag/frameworks.json")["rows"]
        if r["set"] == "원래" and r["impl"] == "직접" and r["kind"] == "hybrid"
    )
    p50 = statistics.median(x["seconds"] for x in now)
    cost = sum(x["cost"] for x in now) / len(now)
    return [
        (
            "① 최종 답 정답성",
            "숫자 · 사실이 사업보고서와 맞나",
            "코드(정답 낱말) + 판사",
            f"{sum(x['correct'] for x in ans)}/{len(ans)}",
            "22편 성적표",
            "ok",
            "문항 16개뿐 · 신뢰구간 없음 → 25 · 31편",
        ),
        (
            "② 근거성 · 인용",
            "문장마다 출처가 있고, 출처가 그 문장을 뒷받침하나",
            "코드(인용 존재) + 판사(지지)",
            f"출처 {sum(x['cited'] for x in now)}/{sent} · 지지 {sum(x['supported'] for x in now)}/{sent}",
            "22편 성적표",
            "ok",
            "지지 판정을 판사 혼자 한다 → 30편",
        ),
        (
            "③ 거절 · 안전 행동",
            "투자 권유 · 근거 없는 전망을 거절하나",
            "코드(거절 감지)",
            f"{sum(x['correct'] for x in ref)}/{len(ref)}",
            "22편 성적표",
            "part",
            "4문항뿐 · 탈옥 · 함정 문항 0개 → 25 · 32편",
        ),
        (
            "④ 도구 사용 궤적",
            "맞는 도구를 골랐나, 인자 · 순서 · 회복은",
            "기록 + 코드",
            f"도구 선택 {sum(x['ok'] for x in tools)}/{len(tools)}",
            "16편 도구 40개",
            "part",
            "선택만 봤다 · 인자 · 횟수 · 회복은 안 봄 → 26 · 32편",
        ),
        (
            "⑤ 검색 품질",
            "필요한 문단을 상위 5개 안에 가져왔나",
            "Recall@5 · MRR",
            f"recall@5 {rag['recall@5']}",
            "11편 하이브리드",
            "part",
            "검색만 따로 쟀다 · 워크벤치 안에서는 안 잼 → 32편",
        ),
        (
            "⑥ 비용 · 지연",
            "질문 하나에 얼마 · 몇 초",
            "기록 집계",
            f"${cost:.4f}/문항 · p50 {p50:.0f}초",
            "22편 성적표",
            "ok",
            "성공 1건당 비용은 안 봄 → 과제 1",
        ),
        (
            "⑦ 판사 자체",
            "판사가 사람 판단과 얼마나 맞나",
            "사람 라벨 · TPR/TNR",
            "맞는 쌍 6/16 인정",
            "13편 심판 시험",
            "no",
            "사람 라벨이 없다 → 30편",
        ),
    ]


def html(rows):
    word = {"ok": "재고 있음", "part": "일부만", "no": "비어 있음"}
    trs = "".join(
        f"<tr><td><b>{a}</b><br><span class=sub>{b}</span></td><td>{c}</td><td class=num>{d}</td><td>{e}</td>"
        f"<td class={s}>{word[s]}</td><td>{g}</td></tr>"
        for a, b, c, d, e, s, g in rows
    )
    return page(
        "평가 대상 지도",
        "<h1>평가 대상 지도 · DART 리서치 에이전트</h1>"
        "<p class=sub>RAG(사업보고서 검색) + 리서치 팀 + MCP 도구 · 숫자는 1~22편 실행 기록에서 읽음</p>"
        "<table><tr><th>측정면</th><th>채점 방법</th><th>지금 숫자</th><th>기록</th><th>상태</th><th>비어 있는 칸</th></tr>"
        f"{trs}</table>",
    )


if __name__ == "__main__":
    rows = build()
    word = {"ok": "재고 있음", "part": "일부만", "no": "비어 있음"}
    for a, _, _, d, e, s, g in rows:
        print(f"{a} — {d} ({e}) · {word[s]}")
    (DATA / "eval_map.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    serve(html(rows), 8823)
