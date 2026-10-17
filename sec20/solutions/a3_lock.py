"""과제 3 풀이: 리서치가 동시에 두 개 들어오면? — 두 요청을 거의 동시에 보내 두 번째가 바로 거절되는지 본다.
uv run python sec20/solutions/a3_lock.py   (서버가 8790에 떠 있어야 한다)
"""

import json
import threading
import time
import urllib.parse
import urllib.request

URL = "http://127.0.0.1:8790/api/research?"
out = {}


def go(name, q):
    t0 = time.time()
    with urllib.request.urlopen(URL + urllib.parse.urlencode({"q": q}), timeout=900) as r:
        for raw in r:
            line = raw.decode().strip()
            if line.startswith("data: "):
                e = json.loads(line[6:])
                if e["type"] in ("done", "error", "budget"):
                    out[name] = (e["type"], e.get("message", ""), round(time.time() - t0, 1))


a = threading.Thread(target=go, args=("A", "카카오 2025년 영업이익 알려줘"))
b = threading.Thread(target=go, args=("B", "현대자동차 2025년 매출 알려줘"))
a.start()
time.sleep(1)
b.start()
a.join()
b.join()
for k in "AB":
    print(k, out[k])
