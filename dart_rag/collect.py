"""회사 4곳 × 2개년 사업보고서를 받아 청크(data/chunks.jsonl)와 재무 데이터를 만든다.
사용: python -m dart_rag.collect"""

import json

from . import dart
from .ingest import ingest

COMPANIES = ["삼성전자", "SK하이닉스", "현대자동차", "카카오"]
YEARS = [2024, 2025]
OUT = dart.ROOT / "data" / "chunks.jsonl"


def main():
    rows, meta = [], []
    for name in COMPANIES:
        corp = dart.find_corp(name)
        reports = dart.annual_reports(corp["corp_code"], YEARS)
        for y in YEARS:
            r = reports.get(y)
            if not r:
                print(f"  {name} {y}: 사업보고서 없음")
                continue
            xml = dart.document(r["rcept_no"])
            ch = ingest(xml, name, y, r["rcept_no"])
            fin = dart.financials(corp["corp_code"], y)
            rows += ch
            meta.append({"corp": name, "corp_code": corp["corp_code"], "year": y, "rcept_no": r["rcept_no"],
                         "report_nm": r["report_nm"].strip(), "chunks": len(ch), "fin_rows": len(fin)})
            print(f"  {name} {y} {r['rcept_no']} 청크 {len(ch)} 재무 {len(fin)}")
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    (dart.ROOT / "data" / "reports.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(f"총 {len(rows)} 청크 → {OUT.relative_to(dart.ROOT)}")


if __name__ == "__main__":
    main()
