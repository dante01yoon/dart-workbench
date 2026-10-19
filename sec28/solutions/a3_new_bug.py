"""28편 과제 3 — 새 버그(더하기가 a + b + 1)를 심고, 답 두 개를 실행으로 채점한다(모델 호출 없음).
① 버그만 고친 답 ② 더하기는 고쳤지만 다른 함수를 지운 답 — 고친 줄만 보면 둘 다 맞아 보인다.
사용: uv run python sec28/solutions/a3_new_bug.py
"""

import importlib.util
import shutil
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("ex", HERE / "02_exec_grade.py")
ex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ex)

good = (ex.SAMPLE / "calc.py").read_text()
for buggy, fixed in ex.BUGS.values():
    good = good.replace(buggy, fixed)  # 원래 버그 셋은 고친 상태
broken = good.replace("return a + b", "return a + b + 1", 1)  # 새 버그 하나만
answers = {
    "① 더하기만 고침": good,
    "② 더하기만 남기고 나머지 함수 지움": "def add(a, b):\n    return a + b\n",
}
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp) / "p"
    shutil.copytree(ex.SAMPLE, root)
    (root / "calc.py").write_text(broken)
    before = ex.tests(root)
    f2p = [t for t, ok in before.items() if not ok]
    p2p = [t for t, ok in before.items() if ok]
    print(f"버그를 심은 뒤: 실패 {f2p} · 통과 {len(p2p)}개")
    for name, code in answers.items():
        (root / "calc.py").write_text(code)
        after = ex.tests(root, before)
        ok = all(after.get(t, False) for t in before)
        print(
            f"{name}: F→P {sum(after.get(t, False) for t in f2p)}/{len(f2p)} · P→P {sum(after.get(t, False) for t in p2p)}/{len(p2p)} → {'✅' if ok else '❌'}"
        )
