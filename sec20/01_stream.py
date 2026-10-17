"""20편 01: 터미널에서 SSE를 받아 진행 이벤트를 한 줄씩 찍는다(서버가 8790에 떠 있어야 한다).
uv run python sec20/01_stream.py "질문" [비용 상한]
"""

import json
import sys
import urllib.parse
import urllib.request

q = sys.argv[1] if len(sys.argv) > 1 else "카카오 2025년 실적과 사업 위험 요인을 정리해 줘"
cap = sys.argv[2] if len(sys.argv) > 2 else "0.05"
url = "http://127.0.0.1:8790/api/research?" + urllib.parse.urlencode({"q": q, "cap": cap})
print(f"■ {q}  (비용 상한 ${cap})\n")
with urllib.request.urlopen(url, timeout=900) as r:
    for raw in r:
        line = raw.decode().strip()
        if not line.startswith("data: "):
            continue
        e = json.loads(line[6:])
        t, k = e.get("t", ""), e["type"]
        if k == "plan":
            print(
                f"{t:>6}초  plan      "
                + " · ".join(f"{x['id']} {x['worker']}({x.get('corp') or '-'})" for x in e["tasks"])
            )
        elif k == "task_start":
            print(f"{t:>6}초  start     {e['id']} {e['worker']} — {e['query'][:30]}")
        elif k == "task_end":
            print(
                f"{t:>6}초  end       {e['id']} 근거 {e['n']}개  (누적 ${e['spent']})"
                + (f"  오류 {e['error']}" if e["error"] else "")
            )
        elif k == "verify":
            print(f"{t:>6}초  verify{e['round']}   지지 {e['ok']}/{e['total']}  (누적 ${e['spent']})")
        elif k == "revise_kept":
            print(f"{t:>6}초  kept      고친 답이 비어 원래 보고서를 유지")
        elif k == "done":
            print(f"{t:>6}초  done      반성 {e['rounds']}회 · ${e['spent']}\n")
            for s in e["report"]:
                print(f"  [{s['badge']}] {s['sentence']} {s['cites']}")
        elif k in ("budget", "error", "refused"):
            print(f"{'':>6}   {k:<9} {e.get('message', '')}")
        else:
            print(f"{t:>6}초  {k}")
