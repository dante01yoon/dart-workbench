"""15편: 공시 검색 MCP 서버를 표준 라이브러리만으로 손으로 만든다.

- 전송: stdio. 한 줄에 JSON-RPC 메시지 하나. stdout에는 메시지만 쓰고, 로그는 stderr로 보낸다.
- 프로토콜: 2026-07-28(요청마다 _meta에 버전, 핸드셰이크 없음) + 예전 클라이언트용 initialize(2025-11-25)
- 도구 3개: list_reports(보고서 목록), get_financials(재무 API 숫자), search_filings(10편 하이브리드 검색)
"""

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sec10"))
sys.path.insert(0, str(HERE.parent / "sec02"))
from tools15 import ROOT, run_tool  # 2편 재무 API 도구를 그대로 쓴다

MODERN = "2026-07-28"
LEGACY = ["2025-11-25", "2025-06-18"]
VERSION_KEY = "io.modelcontextprotocol/protocolVersion"
SERVER_INFO = {"name": "dart-filings", "version": "0.1.0"}
INSTRUCTIONS = "삼성전자 · SK하이닉스 · 현대자동차 · 카카오의 2025 사업보고서(DART)를 찾는 서버. 숫자는 get_financials를 먼저 쓴다."
CORPS = ["삼성전자", "SK하이닉스", "현대자동차", "카카오"]
# 2026-07-28: 목록 결과에는 캐시 필드가 꼭 있어야 한다. NO_CACHE_FIELDS=1이면 일부러 뺀다(15편 실험)
CACHE = {} if os.environ.get("NO_CACHE_FIELDS") else {"ttlMs": 300_000, "cacheScope": "public"}
TRACE = os.environ.get("MCP_TRACE")  # 받은 요청 · 보낸 응답을 파일로 남긴다

TOOLS = [
    {
        "name": "list_reports",
        "description": "검색할 수 있는 사업보고서 목록(회사, 사업연도, 보고서 이름)을 돌려준다.",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "get_financials",
        "description": "재무 API 기준 연결 매출액 · 영업이익 · 당기순이익(당기 · 전기, 원)을 돌려준다. "
        "숫자 질문은 본문 검색보다 이 도구가 정확하다.",
        "inputSchema": {
            "type": "object",
            "properties": {"corp": {"type": "string", "enum": CORPS}},
            "required": ["corp"],
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "search_filings",
        "description": "2025 사업보고서 본문에서 질문과 관련된 조각을 찾는다. 결과마다 회사 · 섹션 경로 · 원문을 준다. "
        "답할 때 섹션 경로를 출처로 적는다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "찾을 내용(자연어)"},
                "corp": {"type": "string", "enum": CORPS},
                "k": {"type": "integer", "minimum": 1, "maximum": 8, "default": 5},
            },
            "required": ["query"],
        },
        "annotations": {"readOnlyHint": True},
    },
]

_store = None


def done(payload):
    """새 방식 결과의 공통 틀: 결과 종류 + 서버 정보(_meta)."""
    return {"resultType": "complete", "_meta": {"io.modelcontextprotocol/serverInfo": SERVER_INFO}, **payload}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def store():
    """처음 검색할 때만 청크와 벡터를 읽는다(서버 시작을 빠르게)."""
    global _store
    if _store is None:
        from cite import Store  # 10편 검색(맥락 붙인 키워드 + 벡터)

        _store = Store()
        log(f"청크 {len(_store.chunks)}개 로드")
    return _store


def call_tool(name, args):
    if name == "list_reports":
        return [
            {"corp": r["corp"], "year": r["year"], "report": r.get("report_nm", "사업보고서")}
            for r in (json.loads(p.read_text()) for p in sorted((ROOT / "data" / "reports").glob("*.json")))
        ]
    if name == "get_financials":
        rows = run_tool("key_accounts", {"corp": args["corp"], "year": 2025}).get("rows", [])
        out = {}
        for r in rows:
            acc = r["account_nm"].split("(")[0]
            if (
                r["fs_nm"].startswith("연결")
                and acc in ("매출액", "영업이익", "당기순이익")
                and acc not in out
            ):
                out[acc] = {"당기": r["thstrm_amount"], "전기": r["frmtrm_amount"]}
        return {
            "corp": args["corp"],
            "year": 2025,
            "unit": "원",
            "source": "DART 재무 API 주요 계정",
            "accounts": out,
        }
    if name == "search_filings":
        s = store()
        ids = s.search(args["query"], args.get("corp"), k=max(1, min(int(args.get("k", 5)), 8)))
        return [
            {
                "corp": s.chunks[i]["corp"],
                "section": s.chunks[i]["section"],
                "text": s.chunks[i]["text"][:1200],
            }
            for i in ids
        ]
    raise KeyError(name)


def handle(msg, state):
    method, params, mid = msg.get("method"), msg.get("params") or {}, msg.get("id")
    if mid is None:  # 알림(id 없음)에는 답하지 않는다
        return None

    def ok(r):
        return {"jsonrpc": "2.0", "id": mid, "result": r}

    def err(code, text, data=None):
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "error": {"code": code, "message": text, **({"data": data} if data else {})},
        }

    caps = {"tools": {}}
    if method == "server/discover":  # 새 클라이언트가 먼저 묻는다: 어떤 버전을 아니?
        return ok(
            done(
                {
                    "supportedVersions": [MODERN, *LEGACY],
                    "capabilities": caps,
                    "instructions": INSTRUCTIONS,
                    **CACHE,
                }
            )
        )
    if method == "initialize":  # 예전 클라이언트의 핸드셰이크
        v = params.get("protocolVersion")
        state["legacy"] = v if v in LEGACY else LEGACY[0]
        return ok(
            {
                "protocolVersion": state["legacy"],
                "capabilities": caps,
                "serverInfo": SERVER_INFO,
                "instructions": INSTRUCTIONS,
            }
        )
    if not state.get("legacy"):  # 새 방식은 요청마다 버전을 확인한다
        v = (params.get("_meta") or {}).get(VERSION_KEY)
        if v != MODERN:
            return err(
                -32022, "Unsupported protocol version", {"supported": [MODERN, *LEGACY], "requested": v}
            )

    if method == "tools/list":
        return ok(done({"tools": TOOLS, **CACHE}))
    if method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        if name not in {t["name"] for t in TOOLS}:
            return err(-32602, f"알 수 없는 도구: {name}")
        try:
            data = call_tool(name, args)
            text = json.dumps(data, ensure_ascii=False)
            return ok(done({"content": [{"type": "text", "text": text}], "isError": False}))
        except Exception as e:  # noqa: BLE001 — 도구 실패는 프로토콜 오류가 아니라 isError 결과로 알린다
            return ok(done({"content": [{"type": "text", "text": f"도구 오류: {e}"}], "isError": True}))
    return err(-32601, f"Method not found: {method}")


def main():
    state = {}
    log("dart-filings MCP 서버 시작 (stdio)")
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            print(
                json.dumps(
                    {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
                ),
                flush=True,
            )
            continue
        resp = handle(msg, state)
        if TRACE:
            with open(TRACE, "a", encoding="utf-8") as f:
                f.write(json.dumps({"in": msg, "out": resp}, ensure_ascii=False) + "\n")
        if resp is not None:
            print(json.dumps(resp, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
