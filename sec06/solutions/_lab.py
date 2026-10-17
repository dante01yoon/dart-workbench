"""풀이 공통: 01_skills.py · 02_subagent.py를 가져온다(파일 이름이 숫자로 시작해 import 문을 못 쓴다)."""

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sk = load("skills_exp", "01_skills.py")
sa = load("subagent", "02_subagent.py")
