"""실습 환경 점검 (강의 0편). 키 값은 출력하지 않고 "설정됨"과 실제 호출 결과만 보여 준다.
사용: uv run python check_setup.py
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OK, NO = "✅", "❌"
results = []


def check(name, fn):
    try:
        detail = fn()
        results.append(True)
        print(f"{OK} {name:24s} {detail}")
    except Exception as e:  # noqa: BLE001 — 점검은 실패 이유만 보여 주고 계속
        results.append(False)
        print(f"{NO} {name:24s} {str(e)[:90]}")


def load_env():
    p = ROOT / ".env"
    if not p.exists():
        raise FileNotFoundError(".env가 없습니다 → cp .env.example .env 후 키를 채우세요")
    for line in p.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    return "읽음"


def need(key):
    if not os.environ.get(key):
        raise KeyError(f"{key}가 비어 있습니다")
    return "설정됨"


def http_json(url, data=None, headers=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def dart():
    q = urllib.parse.urlencode(
        {
            "crtfc_key": os.environ["DART_API_KEY"],
            "corp_code": "00126380",
            "bgn_de": "20260101",
            "pblntf_ty": "A",
        }
    )
    d = http_json(f"https://opendart.fss.or.kr/api/list.json?{q}")
    if d.get("status") != "000":
        raise RuntimeError(f"{d.get('status')} {d.get('message')}")
    return f"정상 · 삼성전자 정기공시 {len(d.get('list', []))}건"


def openrouter():
    d = http_json(
        os.environ["OPENAI_BASE_URL"].rstrip("/") + "/embeddings",
        {"model": os.environ.get("EMBED_MODEL", "openai/text-embedding-3-small"), "input": ["점검"]},
        {"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"},
    )
    return f"정상 · 임베딩 {len(d['data'][0]['embedding'])}차원"


def tavily():
    d = http_json(
        "https://api.tavily.com/search",
        {"query": "OpenDART", "max_results": 1},
        {"Authorization": "Bearer " + os.environ["TAVILY_API_KEY"], "Content-Type": "application/json"},
    )
    return f"정상 · 검색 {len(d.get('results', []))}건"


print(f"실습 환경 점검 — {ROOT.name}\n")
check(
    "Python 3.12 이상",
    lambda: (
        f"{sys.version.split()[0]}"
        if sys.version_info >= (3, 12)
        else (_ for _ in ()).throw(RuntimeError(sys.version.split()[0]))
    ),
)
check("uv", lambda: subprocess.run(["uv", "--version"], capture_output=True, text=True).stdout.strip())
check(
    "Node.js (캡스톤 화면)",
    lambda: (
        subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
        if shutil.which("node")
        else (_ for _ in ()).throw(RuntimeError("없음 — 20편 전까지 설치"))
    ),
)
check(
    "패키지 (numpy · mcp)",
    lambda: (
        __import__("numpy").__version__ + " · mcp " + __import__("importlib.metadata").metadata.version("mcp")
    ),
)
check(".env", load_env)
for key in ("DART_API_KEY", "OPENAI_API_KEY", "TAVILY_API_KEY"):
    check(key, lambda key=key: need(key))
check("OpenDART 호출", dart)
check("OpenRouter 호출", openrouter)
check("Tavily 호출", tavily)
print(
    f"\n{sum(results)}/{len(results)} 통과"
    + (" — 준비 완료!" if all(results) else " — ❌ 항목을 고친 뒤 다시 실행하세요")
)
