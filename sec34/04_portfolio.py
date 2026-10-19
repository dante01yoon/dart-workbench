"""34편 ④ 포트폴리오 — 이 섹션(23~34편) 결과를 GitHub README · 이력서 문장 · 공고 역량 지도로. 모델 호출 0.

- 숫자는 모두 각 편 README의 실측(아래 FACTS, 편 번호를 붙여 둔다)과 이번 편 data/compare34.json에서 온다.
- sec34/PORTFOLIO.md를 만들고(GitHub가 그대로 보여 준다), 같은 내용을 화면으로 띄운다.
사용: uv run python sec34/04_portfolio.py   → sec34/PORTFOLIO.md · http://127.0.0.1:8843
"""

import html
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "sec23"))
from page import page, serve

C = json.loads((ROOT / "data" / "compare34.json").read_text())
JOBS = json.loads((ROOT / "sec23" / "jobs.json").read_text())
fix, reg, al = C["fix"], C["regression"], C["all"]
pct = lambda x: f"{x * 100:.0f}%"
pp = lambda x: f"{x * 100:+.0f}%p"

# 각 편 README의 실측(2026-10-19). (편, 내용) — 포트폴리오에 쓰는 숫자는 여기서만 가져온다.
FACTS = {
    "dataset": (
        "25",
        "실행 기록 질문 127개 → 시험지 v2 67문항(개발 48 · held-out 19), 보고서형 12문항은 원래 문항 은행에 0개였다",
    ),
    "error": (
        "26",
        "개발 53문항 중 틀림 12 · 메모 14 → 처음 틀어진 단계: 계획 6 · 공시 검색 5 · 채점기 1 · 재무 조회 1 · 작성 1",
    ),
    "rubric": (
        "27",
        "루브릭 v1 예/아니오 기준 6개(R1~R6), 코드 기준 모두 통과 40/53. 1~5점은 같은 답에 2~4점으로 흔들림",
    ),
    "grader": (
        "28",
        "코드 채점기 v3 · 테스트 12개, 사람 메모와 일치 51 → 53/53. 실행 채점 24/24(.pyc 캐시 버그를 찾아 고침)",
    ),
    "judge": ("29", "LLM 판사 v2: 넣은 거짓 문장 8/8 검출, 쌍 비교 순서 바꾸기 갈림 0/18"),
    "validation": (
        "30",
        "사람 라벨 14개(실패 5): 판사 v2 TPR 5/5(95% 57~100%) · kappa 1.00 — dev 성적, 라벨러 1명",
    ),
    "stats": ("31", "개발 48문항 81%(95% 70~92%), 48문항으로 잡을 수 있는 최소 차이 17%p, pass^3 13/20"),
    "agent": (
        "32",
        "검색 Recall@6 84% · MRR 0.66, 근거 판사 지지 93%, 도구 궤적 47/53, 레드팀 9/9(가짜 사실 문장은 4번 중 3번 뚫림)",
    ),
    "gate": (
        "33",
        "GitHub Actions 회귀 관문(저장된 출력 재채점 · 모델 호출 0 · 4~5초): 실제 PR에서 회귀 5문항을 막음",
    ),
}

IMPROVE = (
    f"계획 담당 지시문 한 곳을 고쳐 계획 실패 {fix['n']}문항 {fix['before']}/{fix['n']} → {fix['after']}/{fix['n']}"
    f"(95% {pct(fix['after_ci'][0])}~{pct(fix['after_ci'][1])}), 회귀 세트 {reg['after']}/{reg['n']}"
    + (" — 관문 통과" if not C["lost"] else f" — 관문 실패({' '.join(C['lost'])})")
)

README = f"""# DART 공시 리서치 에이전트 — 평가 시스템

> 단테의 From Scratch #2 실전 8 · AI 평가(23~34편) 결과를 한 장으로. 숫자는 모두 이 저장소의 실행 기록에서 나왔다(2026-10-19, deepseek-v4-flash).

## 1. 문제
삼성전자 · SK하이닉스 · 현대자동차 · 카카오의 2025년 사업보고서로 답하는 리서치 에이전트(RAG + 멀티 에이전트 + MCP).
틀린 숫자, 공시에 없는 전망을 사실처럼 말하기, 투자 권유가 가장 위험하다 → 이 셋을 먼저 잰다.

## 2. 평가 대상
| 측정면 | 지표 | 결과 | 편 |
|---|---|---|---|
| 최종 답 정답성 | 코드 채점기 v3 | 개발 48문항 81% (95% 70~92%) | 28 · 31 |
| 근거성 · 인용 | 출처 · 숫자 대조 · 판사 지지 | 판사 지지 93% (226문장) | 32 |
| 검색 | Recall@k · MRR | Recall@6 84% · MRR 0.66 (19문항) | 32 |
| 도구 궤적 | 도구 · 인자 · 중복 | 47/53 | 32 |
| 거절 · 안전 | 레드팀 9문항 | 9/9, 단 가짜 사실 문장은 4번 중 3번 뚫림 | 32 |
| 비용 · 지연 | 문항당 중앙값 | $0.0049 · 180초, 성공 1건당 $0.0087 | 32 |
| 판사 자체 | TPR/TNR · kappa | 아래 5절 | 30 |

## 3. 데이터셋 · 라벨
- {FACTS["dataset"][1]} (25편)
- 사람 라벨: 26편 메모 14개를 결정권자 한 명이 검토 · 승인, 지침 v1 = 루브릭 (30편)

## 4. 채점기 · 루브릭
- {FACTS["rubric"][1]} (27편)
- {FACTS["grader"][1]} (28편)
- {FACTS["judge"][1]} (29편)

## 5. 판사 검증
- {FACTS["validation"][1]} (30편)
- 일치율만 보면 속는다: "항상 통과"도 일치 77.4%, 하지만 TPR 0 · kappa 0

## 6. 통계
- {FACTS["stats"][1]} (31편)

## 7. 회귀 관문
- 회귀 세트 35(여러 번 돌려 늘 맞힌 문항) · 능력 세트 18. 회귀는 문항 단위로 막는다 (33편)
- {FACTS["gate"][1]}

## 8. 개선 한 바퀴 (34편)
- 오류 분석 → 가장 큰 칸(계획 6) → 한 곳 수정 → 영향받은 문항 + 회귀 세트만 다시 실행 → 관문
- {IMPROVE}
- 다시 돌린 {al["n"]}문항 짝 비교: {pp(al["diff"])} (95% {pp(al["diff_ci"][0])} ~ {pp(al["diff_ci"][1])}), 다시 돌리기 비용 ${C["cost"]["rerun_total"]:.2f}

## 9. 한계
- 라벨러 한 명, 판사 검증은 dev 성적(손대지 않은 test 라벨 없음), 실패 라벨 5개라 구간이 넓다
- 문항이 적다(개발 48): 17%p보다 작은 차이는 평균으로 말할 수 없다
- 운영 트래픽이 없다: 온라인 신호는 26편 기록을 운영 로그라고 친 계산이다
- 개선 한 바퀴에서 능력 세트 나머지 12문항은 다시 돌리지 않았다(비용)

## 10. 다시 해 보기
```bash
python3 sec33/01_gate.py --runs planner_v2   # 회귀 관문(모델 호출 0)
uv run python sec34/03_compare.py            # 전후 비교 + 신뢰구간
```
"""

GOOD = [
    "DART 공시 리서치 에이전트(RAG · 멀티 에이전트 · MCP)의 평가 파이프라인을 만들었다: 실행 기록에서 시험지 67문항(개발 48 · held-out 19), 코드 채점기 v3(사람 판정 일치 53/53), LLM 판사(사람 라벨 14개로 TPR 5/5 · 95% 57~100%)",
    "GitHub Actions 회귀 관문(저장된 출력 재채점, 모델 호출 0, 4~5초)을 붙여 답을 줄이는 PR이 회귀 5문항을 깨뜨린 것을 병합 전에 막았다",
    f"오류 분석으로 가장 큰 실패 단계(계획, 12개 중 6개)를 찾아 지시문 한 곳을 고쳤다: 해당 문항 {fix['before']}/{fix['n']} → {fix['after']}/{fix['n']}"
    + (
        f", 회귀 세트 {reg['after']}/{reg['n']}로 관문 통과"
        if not C["lost"]
        else f". 회귀 관문이 {len(C['lost'])}문항 하락({reg['after']}/{reg['n']})을 잡아 병합하지 않고 원인을 나눠 봤다"
    ),
]
BAD = [
    ("에이전트 정확도를 95%로 끌어올렸다", "어느 시험지 · 몇 문항 · 무엇과 비교? 우리 기록에 95%는 없다"),
    ("LLM 판사가 사람과 100% 일치", "14개 · dev 성적 · 라벨러 1명 — 구간 57~100%를 빼면 부풀린 말"),
    ("대규모 평가 플랫폼 구축", "53문항 · 혼자 · 운영 트래픽 없음. 규모 대신 무엇을 막았는지로 쓴다"),
]
EN = (
    "Built an eval pipeline for a RAG research agent over Korean SEC-style filings: 67-item test set from production-style traces "
    "(48 dev / 19 held-out), code grader validated against human review (53/53), LLM judge validated on 14 human labels "
    "(TPR 5/5, 95% CI 57-100%), and a CI regression gate that blocked a PR breaking 5 regression items."
)

# 공고 역량 10개(Python은 실습 언어라 빼고 공고 수 순) × 23~34편 — 역량별 편은 23편 jobs.json의 매핑 + 34편
cnt = Counter(s for j in JOBS["jobs"] for s in j["skills"])
TOP = [s for s in JOBS["skills"] if s["id"] != "python"][:10]
MORE = [
    s for s in JOBS["skills"] if s["id"] in ("stats", "calib", "bench")
]  # 공고엔 드물지만 면접 자료에 자주 나온다
EXTRA34 = {"error", "ci", "stats"}  # 34편 개선 한 바퀴가 다시 쓰는 것
LESSONS = list(range(23, 35))


def covers(skill, n):
    return str(n) in skill["lesson"].replace(" ", "").split("·") or (n == 34 and skill["id"] in EXTRA34)


assert len(TOP) == 10 and all(any(covers(s, n) for n in LESSONS) for s in TOP)  # 빈 역량이 있으면 멈춘다


def md_table_html(text):
    """README의 표 · 목록 · 제목만 화면용 HTML로(외부 라이브러리 없이 — 이 README에 쓴 문법만)."""
    out, rows, code = [], [], False
    for line in text.splitlines():
        if line.startswith("```"):
            out.append("<pre>" if not code else "</pre>")
            code = not code
            continue
        if code:
            out.append(html.escape(line))
            continue
        if line.startswith("|"):
            if not line.startswith("|---"):
                rows.append([html.escape(c.strip()) for c in line.strip("|").split("|")])
            continue
        if rows:
            out.append("<table>" + "".join(
                "<tr>" + "".join(f"<{'th' if i == 0 else 'td'}>{c}</{'th' if i == 0 else 'td'}>" for c in r) + "</tr>"
                for i, r in enumerate(rows)) + "</table>")  # fmt: skip
            rows = []
        e = html.escape(line)
        if line.startswith("# "):
            out.append(f"<h3 class=rt>{e[2:]}</h3>")
        elif line.startswith("## "):
            out.append(f"<h4>{e[3:]}</h4>")
        elif line.startswith("&gt; "):
            out.append(f"<p class=sub>{e[5:]}</p>")
        elif line.startswith("- "):
            out.append(f"<li>{e[2:]}</li>")
        elif line:
            out.append(f"<p>{e}</p>")
    return "\n".join(out)


CSS = """<style>
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.tile{background:#1d2028;border:1px solid #2c303a;border-radius:14px;padding:18px 22px}
.tile .k{color:#9aa0aa;font-size:20px}.tile .v{font:600 44px 'JetBrains Mono',monospace;margin:6px 0}
.tile .s{color:#9aa0aa;font-size:18px}
.items{display:grid;grid-template-columns:repeat(2,1fr);gap:6px 28px;font-size:19px}
.it{display:grid;grid-template-columns:62px 52px 52px 1fr;align-items:center;gap:8px;border-bottom:1px solid #2c303a;padding:3px 0}
.it .q{color:#9aa0aa;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.b{display:inline-block;width:40px;text-align:center;border-radius:6px;padding:1px 0;font-weight:700}
.b.y{background:#21492b;color:#7fd18b}.b.n{background:#4f2523;color:#ef7a6b}
.readme{background:#0f1115;border:1px solid #2c303a;border-radius:14px;padding:10px 34px 24px;font-size:20px}
.readme h3.rt{font-size:32px;margin:18px 0 4px}.readme h4{font-size:24px;color:#f2b84b;margin:22px 0 8px}
.readme table{font-size:19px}.readme li{margin:3px 0 3px 18px}
pre{background:#1d2028;padding:12px 16px;border-radius:10px;font:18px 'JetBrains Mono',monospace;white-space:pre-wrap}
.good li{color:#e8e6e1;margin:8px 0}.bad td:first-child{color:#ef7a6b;text-decoration:line-through}
.map td,.map th{text-align:center;padding:7px 6px}.map td:first-child,.map th:first-child{text-align:left}
.map .on{color:#f2b84b;font-size:24px}.map .dim td{opacity:.6}
</style>"""


def row(s, cls=""):
    cells = "".join(f"<td class=on>{'●' if covers(s, n) else ''}</td>" for n in LESSONS)
    return f"<tr class='{cls}'><td>{html.escape(s['name'])} <span class=num>({cnt[s['id']]})</span></td>{cells}</tr>"


def tile(k, v, s):
    return f"<div class=tile><div class=k>{k}</div><div class=v>{v}</div><div class=s>{s}</div></div>"


def badge(ok):
    return f"<span class='b {'y' if ok else 'n'}'>{'O' if ok else 'X'}</span>"


def build():
    gate = "통과" if not C["lost"] else f"실패 {len(C['lost'])}"
    items = C["items"]
    order = [i for i in items if items[i]["split"] != "regression"] + [
        i for i in items if items[i]["split"] == "regression"
    ]
    grid = "".join(
        f"<div class=it><span class=num>{i}</span>{badge(items[i]['before'])}{badge(items[i]['after'])}"
        f"<span class=q>{html.escape(items[i]['q'])}</span></div>"
        for i in order
    )
    body = f"""{CSS}
<h1>34편 · 개선 한 바퀴와 포트폴리오</h1>
<p class=sub>계획 담당 지시문 v1 → v2 · 같은 문항을 다시 돌려 코드 채점기 v3로 · 모델 deepseek-v4-flash · 2026-10-19</p>
<h2 id=ba>전후 성적표</h2>
<div class=tiles>
{tile("고치려던 계획 실패", f"{fix['before']} → {fix['after']} / {fix['n']}", f"후 95% {pct(fix['after_ci'][0])}~{pct(fix['after_ci'][1])}")}
{tile("회귀 세트(관문)", f"{reg['after']} / {reg['n']}", f"관문 {gate} · 전 {reg['before']}/{reg['n']}")}
{tile(f"다시 돌린 {al['n']}문항 짝 비교", pp(al["diff"]), f"95% {pp(al['diff_ci'][0])} ~ {pp(al['diff_ci'][1])}")}
{tile("문항당 비용(중앙값)", f"${C['cost']['median_after']:.4f}", f"전 ${C['cost']['median_before']:.4f} · 합계 ${C['cost']['rerun_total']:.2f}")}
</div>
<p class=sub style="margin-top:18px">문항별 전 → 후 (위: 계획 실패 {fix["n"]} · 아래: 회귀 세트 {reg["n"]})</p>
<div class=items>{grid}</div>
<h2 id=readme>GitHub README (sec34/PORTFOLIO.md)</h2>
<div class=readme>{md_table_html(README)}</div>
<h2 id=resume>이력서 문장 — 숫자는 기록에 있는 것만</h2>
<ul class=good>{"".join(f"<li>{html.escape(g)}</li>" for g in GOOD)}</ul>
<p class=sub>영문 예: {html.escape(EN)}</p>
<table class=bad><tr><th>쓰지 않을 문장</th><th>왜</th></tr>{"".join(f"<tr><td>{html.escape(a)}</td><td>{html.escape(b)}</td></tr>" for a, b in BAD)}</table>
<h2 id=map>23~34편 × 공고 역량 10개</h2>
<table class=map><tr><th>역량 (공고 12개 중)</th>{"".join(f"<th>{n}</th>" for n in LESSONS)}</tr>
{"".join(row(s) for s in TOP)}
<tr><td colspan=13 class=sub style="text-align:left;padding-top:16px">공고엔 드물지만 면접 준비 자료에 자주 나오는 것</td></tr>
{"".join(row(s, "dim") for s in MORE)}
</table>
<p class=sub>Python(8)은 모든 편의 실습 언어. 사후학습 · RL 연계(4)는 모델 연구소 직무용이라 다루지 않았다.</p>"""
    return page("34편 포트폴리오", body)


if __name__ == "__main__":
    (HERE / "PORTFOLIO.md").write_text(
        README.replace("~", r"\~")
    )  # GitHub는 ~ 두 개 사이를 취소선으로 그린다
    print(f"README → sec34/PORTFOLIO.md ({len(README.splitlines())}줄)")
    print("이력서 문장:")
    for g in GOOD:
        print("  -", g)
    serve(build(), 8843)
