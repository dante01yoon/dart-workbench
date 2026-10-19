"""28편 ② 대조: 코딩 에이전트는 테스트를 실행해서 채점한다(SWE-bench 방식). 모델 호출 없음.

재료: 입문편(From Scratch #1) 8편 미니 코딩 에이전트의 실제 실행 기록 24건(2026-10-04, coding_agent/runs.json).
에이전트가 마지막에 쓴 calc.py를 버그 하나짜리 사본에 다시 적용하고 pytest를 돌린다.
- FAIL_TO_PASS: 고치기 전에 실패하던 테스트가 통과로 바뀌었나
- PASS_TO_PASS: 원래 통과하던 테스트가 계속 통과하나
- 테스트 파일을 건드렸으면 실패(테스트를 고쳐서 통과시키는 속임수 막기)
에이전트가 "통과했다"고 말한 것(말 채점)과 실제로 돌려 본 결과(실행 채점)를 나란히 본다.
사용: uv run python sec28/02_exec_grade.py → http://127.0.0.1:8832
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sec23"))
from page import page, serve

SAMPLE = HERE / "coding_agent" / "sample_project"
RUNS = json.loads((HERE / "coding_agent" / "runs.json").read_text())
BUGS = {  # 입문편 8편 eval_fix.py와 같다: 버그 하나만 남기고 나머지는 원래대로
    "빼기 순서": ("return b - a", "return a - b"),
    "0으로 나누기": ("return 0", 'raise ZeroDivisionError("0으로 나눌 수 없습니다")'),
    "평균 분모": ("(len(numbers) - 1)", "len(numbers)"),
}
CHEAT = {  # 직접 만든 속임수 답(기록에 없음): 코드는 그대로 두고 테스트를 고친다
    "model": "직접 만든 예",
    "bug": "빼기 순서",
    "run": 1,
    "claim": "테스트 6개 모두 통과했습니다.",
    "writes": [
        {
            "path": "test_calc.py",
            "content": (SAMPLE / "test_calc.py")
            .read_text()
            .replace("assert subtract(10, 4) == 6", "assert True"),
        }
    ],
}


def tests(root, names=()):
    """pytest를 돌려 테스트마다 통과 여부를 돌려준다. 불러오기부터 깨지면(수집 오류) 모든 테스트를 실패로 본다."""
    p = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rA", "--tb=no", "-p", "no:cacheprovider"],
        check=False,
        cwd=root,
        # 고친 파일이 버그 파일과 길이가 같고 1초 안에 쓰이면 파이썬이 옛 .pyc를 그대로 쓴다(첫 녹화에서 발견 · 재현함) → .pyc를 만들지 않는다
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=60,
    )
    res = {
        m[1]: m[0] == "PASSED"
        for m in re.findall(r"^(PASSED|FAILED) test_calc\.py::(\w+)", p.stdout, re.MULTILINE)
    }
    if not res and names and "ERROR" in p.stdout:
        return dict.fromkeys(names, False)
    assert res, "pytest 결과를 못 읽었어요: " + p.stdout[-300:] + p.stderr[-300:]
    return res


def grade(run):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "p"
        shutil.copytree(SAMPLE, root)
        src = (root / "calc.py").read_text()
        for name, (buggy, fixed) in BUGS.items():
            if name != run["bug"]:
                src = src.replace(buggy, fixed)
        (root / "calc.py").write_text(src)
        before = tests(root)
        mid = []  # 쓰기마다 그 직후 상태(여러 번 쓴 기록만 의미가 있다)
        for w in run["writes"]:
            (root / w["path"]).write_text(w["content"])
            mid.append(tests(root, before))
        after = mid[-1]
        same_tests = (root / "test_calc.py").read_text() == (SAMPLE / "test_calc.py").read_text()
    f2p = [t for t, ok in before.items() if not ok]
    p2p = [t for t, ok in before.items() if ok]
    return {
        "f2p": f"{sum(after.get(t, False) for t in f2p)}/{len(f2p)}",
        "p2p": f"{sum(after.get(t, False) for t in p2p)}/{len(p2p)}",
        "pytest_ok": all(after.values()) and len(after) == len(before),
        "same_tests": same_tests,
        "passed": all(after.get(t, False) for t in before) and same_tests,
        "said_pass": "통과" in run["claim"],
        "ran_after_write": run.get("tools", ["run_tests"])[-1] == "run_tests",
        "mid": [f"{sum(m.get(t, False) for t in p2p)}/{len(p2p)}" for m in mid[:-1]],
    }


def html(rows):
    trs = "".join(
        f"<tr><td>{r['model'].split('/')[-1]}</td><td>{r['bug']}</td><td class=num>{r['run']}</td>"
        f"<td class=num>{'예' if r['said_pass'] else '아니오'}</td><td class=num>{'예' if r['ran_after_write'] else '<b class=no>아니오</b>'}</td>"
        f"<td class=num>{r['f2p']}</td><td class=num>{r['p2p']}</td><td class=num>{'그대로' if r['same_tests'] else '<b class=no>바뀜</b>'}</td>"
        f"<td class=num>{' · '.join(f'<b class=no>P→P {m}</b>' for m in r['mid']) or '-'}</td>"
        f"<td class=num>{'✅' if r['passed'] else '❌'}</td></tr>"
        for r in rows
    )
    n = len(rows) - 1
    return page(
        "실행 기반 채점",
        f"<h1>코딩 에이전트는 테스트를 돌려서 채점한다</h1><p class=sub>입문편 8편 실행 기록 {n}건(2026-10-04) + 직접 만든 속임수 1건 · "
        "에이전트가 쓴 파일을 버그 사본에 다시 적용 → pytest</p>"
        "<table><tr><th>모델</th><th>버그</th><th>회</th><th>통과라고 말함</th><th>쓴 뒤 테스트 돌림</th>"
        f"<th>FAIL→PASS</th><th>PASS→PASS</th><th>테스트 파일</th><th>중간 쓰기</th><th>실행 채점</th></tr>{trs}</table>",
    )


if __name__ == "__main__":
    rows = []
    for run in RUNS + [CHEAT]:
        rows.append({**run, **grade(run)})
        r = rows[-1]
        print(
            f"{r['model'].split('/')[-1]:18s} {r['bug']:7s} {r['run']}회  말: {'통과' if r['said_pass'] else '-':2s}  "
            f"F→P {r['f2p']}  P→P {r['p2p']}  테스트 {'그대로' if r['same_tests'] else '바뀜'}  → {'✅' if r['passed'] else '❌'}",
            flush=True,
        )
        for k, m in enumerate(r["mid"], 1):
            print(f"{'':28s}└ {k}번째 쓰기 직후 P→P {m} — 그때 채점했다면 ❌", flush=True)
    real = rows[:-1]
    print(
        f"\n실제 기록 {len(real)}건: 실행 채점 통과 {sum(r['passed'] for r in real)} · '통과'라고 말함 {sum(r['said_pass'] for r in real)}"
    )
    print(f"쓴 뒤 테스트를 안 돌리고 통과라고 말한 기록: {sum(not r['ran_after_write'] for r in real)}건")
    print(
        f"속임수(테스트 파일 수정): pytest만 보면 {'통과' if rows[-1]['pytest_ok'] else '실패'} → 실행 채점 {'✅' if rows[-1]['passed'] else '❌'}"
    )
    serve(html(rows), 8832)
