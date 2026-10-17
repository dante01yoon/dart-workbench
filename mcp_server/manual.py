"""공시 검색 MCP 서버 — 표준 라이브러리만으로 손으로 구현 (강의 15편).

전송: stdio, 줄 단위 JSON-RPC 2.0. stdout에는 JSON-RPC 메시지만 쓴다(로그는 stderr).
프로토콜: 2026-07-28(무상태, 요청마다 _meta에 버전) + 2025-11-25(initialize 핸드셰이크) 둘 다 받는 "dual-era" 서버.
  - 새 클라이언트: server/discover로 지원 버전 확인 → 요청마다 _meta["io.modelcontextprotocol/protocolVersion"]
  - 예전 클라이언트: initialize → notifications/initialized → tools/list, tools/call
도구: list_reports, get_financials, search_report
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dart_rag import dart  # noqa: E402
from dart_rag.search import Searcher, load_chunks  # noqa: E402

MODERN = "2026-07-28"
LEGACY = ["2025-11-25", "2025-06-18"]
SERVER_INFO = {"name": "dart-filings", "version": "0.1.0"}
INSTRUCTIONS = "삼성전자·SK하이닉스·현대자동차·카카오의 2024·2025 사업보고서(DART)를 찾는 서버. 숫자는 get_financials를 먼저 쓴다."

TOOLS = [
    {
        "name": "list_reports",
        "description": "검색할 수 있는 사업보고서 목록(회사, 사업연도, 접수번호)을 돌려준다.",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "get_financials",
        "description": "재무 API(XBRL) 기준 연결 손익 숫자를 원 단위로 돌려준다. 매출액·영업이익·당기순이익 질문은 본문 검색보다 이 도구가 정확하다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "corp": {"type": "string", "enum": ["삼성전자", "SK하이닉스", "현대자동차", "카카오"]},
                "year": {"type": "integer", "enum": [2024, 2025]},
            },
            "required": ["corp", "year"],
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "search_report",
        "description": "사업보고서 본문에서 질문과 관련된 조각을 찾는다. 결과마다 회사·연도·섹션 경로와 원문을 준다. 답할 때 섹션 경로를 출처로 적는다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "찾을 내용(자연어)"},
                "corp": {"type": "string", "enum": ["삼성전자", "SK하이닉스", "현대자동차", "카카오"]},
                "year": {"type": "integer", "enum": [2024, 2025]},
                "k": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
            },
            "required": ["query"],
        },
        "annotations": {"readOnlyHint": True},
    },
]

ACCOUNTS = {"ifrs-full_Revenue": "매출액", "dart_OperatingIncomeLoss": "영업이익", "ifrs-full_ProfitLoss": "당기순이익"}
_searcher = None
TRACE = __import__("os").environ.get("MCP_TRACE")  # 받은 요청·응답을 파일로 남겨 디버깅


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def searcher():
    """처음 검색할 때만 청크를 읽는다(서버 시작을 빠르게). 벡터 파일이 있으면 하이브리드, 없으면 키워드."""
    global _searcher
    if _searcher is None and __import__("os").environ.get("DART_LEAN"):
        from dart_rag.lean import LeanSearcher  # 배포: 압축 색인(약 100MB)

        _searcher = LeanSearcher()
        log(f"LeanSearcher: 청크 {len(_searcher.chunks)}개")
    if _searcher is None:
        chunks = load_chunks()
        emb = dart.ROOT / "data" / "emb.npy"
        vec = None
        if emb.exists():
            import numpy as np

            vec = np.load(emb)
        _searcher = Searcher(chunks, vec)
        log(f"청크 {len(chunks)}개 로드, 벡터 {'있음' if vec is not None else '없음'}")
    return _searcher


def call_tool(name, args):
    if name == "list_reports":
        rows = json.loads((dart.ROOT / "data" / "reports.json").read_text())
        return [{k: r[k] for k in ("corp", "year", "rcept_no", "report_nm")} for r in rows]
    if name == "get_financials":
        meta = next((r for r in json.loads((dart.ROOT / "data" / "reports.json").read_text())
                     if r["corp"] == args["corp"] and r["year"] == args["year"]), None)
        if not meta:
            raise ValueError(f"{args['corp']} {args['year']} 보고서가 없습니다")
        rows = dart.financials(meta["corp_code"], args["year"])
        out = {}
        for r in rows:  # 같은 계정이 자본변동표에도 여러 번 나온다 → 손익계산서(IS/CIS)만
            if r["sj_div"] in ("IS", "CIS") and r["account_id"] in ACCOUNTS and ACCOUNTS[r["account_id"]] not in out:
                out[ACCOUNTS[r["account_id"]]] = {"당기": int(r["thstrm_amount"]), "전기": int(r["frmtrm_amount"])}
        return {"corp": args["corp"], "year": args["year"], "unit": "원", "source": f"DART 재무 API, 접수번호 {meta['rcept_no']}", "accounts": out}
    if name == "search_report":
        s = searcher()
        f = {k: args[k] for k in ("corp", "year") if args.get(k)}
        method = "hybrid" if s.vec is not None else "keyword"
        ids = getattr(s, method)(args["query"], k=int(args.get("k", 5)), **f)
        return [{"corp": s.chunks[i]["corp"], "year": s.chunks[i]["year"], "section": s.chunks[i]["section"],
                 "text": s.chunks[i]["text"][:1500]} for i in ids]
    raise KeyError(name)


CACHE = {"ttlMs": 300_000, "cacheScope": "public"}  # 2026-07-28: 목록·discover 결과는 캐시 필드가 필수(빠지면 클라이언트가 조용히 버린다)


def result(payload):
    return {"resultType": "complete", "_meta": {"io.modelcontextprotocol/serverInfo": SERVER_INFO}, **payload}


def handle(msg, state):
    method, params, mid = msg.get("method"), msg.get("params") or {}, msg.get("id")
    if mid is None:  # 알림(notifications/initialized, notifications/cancelled)은 응답하지 않는다
        return None

    def ok(r):
        return {"jsonrpc": "2.0", "id": mid, "result": r}

    def err(code, text, data=None):
        e = {"code": code, "message": text}
        if data is not None:
            e["data"] = data
        return {"jsonrpc": "2.0", "id": mid, "error": e}

    caps = {"tools": {}}
    if method == "server/discover":
        return ok(result({"supportedVersions": [MODERN, *LEGACY], "capabilities": caps,
                          "instructions": INSTRUCTIONS, **CACHE}))
    if method == "initialize":  # 예전 클라이언트
        v = params.get("protocolVersion")
        state["legacy"] = v if v in LEGACY else LEGACY[0]
        return ok({"protocolVersion": state["legacy"], "capabilities": caps, "serverInfo": SERVER_INFO, "instructions": INSTRUCTIONS})

    if not state.get("legacy"):  # 새 방식: 요청마다 버전을 확인한다
        v = (params.get("_meta") or {}).get("io.modelcontextprotocol/protocolVersion")
        if v != MODERN:
            return err(-32022, "Unsupported protocol version", {"supported": [MODERN, *LEGACY], "requested": v})

    if method == "tools/list":
        return ok(result({"tools": TOOLS, **CACHE}))
    if method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        if name not in {t["name"] for t in TOOLS}:
            return err(-32602, f"알 수 없는 도구: {name}")
        try:
            data = call_tool(name, args)
            return ok(result({"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
                              "structuredContent": {"result": data}, "isError": False}))
        except Exception as e:  # noqa: BLE001 — 도구 실패는 프로토콜 오류가 아니라 isError 결과로 돌려준다
            return ok(result({"content": [{"type": "text", "text": f"도구 오류: {e}"}], "isError": True}))
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
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}), flush=True)
            continue
        resp = handle(msg, state)
        if TRACE:
            with open(TRACE, "a", encoding="utf-8") as f:
                f.write(json.dumps({"in": msg, "out": resp}, ensure_ascii=False)[:1500] + "\n")
        if resp is not None:
            print(json.dumps(resp, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
