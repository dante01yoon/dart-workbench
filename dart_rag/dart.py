"""OpenDART API 클라이언트. 키는 .env의 DART_API_KEY에서 읽고, 화면에 출력하지 않는다.

공식 가이드: https://opendart.fss.or.kr/guide/main.do
- 키는 1인 1개, 공유 금지. 하루 약 2만 건을 넘으면 status 020.
- 원문(document.xml)은 저장소에 넣지 않는다. data/raw/에만 받아 둔다(.gitignore).
"""

import io
import json
import os
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
API = "https://opendart.fss.or.kr/api/"


def load_env(path=ROOT / ".env"):
    if not Path(path).exists():  # 배포 서버에는 .env가 없다(환경 변수로 받는다)
        return
    for line in Path(path).read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


load_env()


class DartError(Exception):
    pass


def _get(path, **params):
    params["crtfc_key"] = os.environ["DART_API_KEY"]
    url = API + path + "?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def _json(path, **params):
    data = json.loads(_get(path, **params))
    if data.get("status") not in ("000", "013"):  # 013 = 조회된 데이터 없음
        raise DartError(f"{path}: {data.get('status')} {data.get('message')}")
    return data


def corp_codes():
    """전체 회사 고유번호 목록(corpCode.xml ZIP). 한 번 받아서 캐시한다."""
    cache = RAW / "corp_codes.json"
    if cache.exists():
        return json.loads(cache.read_text())
    import xml.etree.ElementTree as ET

    z = zipfile.ZipFile(io.BytesIO(_get("corpCode.xml")))
    root = ET.fromstring(z.read(z.namelist()[0]))
    rows = [
        {"corp_code": e.findtext("corp_code"), "corp_name": e.findtext("corp_name"), "stock_code": (e.findtext("stock_code") or "").strip()}
        for e in root.iter("list")
    ]
    RAW.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rows, ensure_ascii=False))
    return rows


def find_corp(name):
    """상장사 중 이름이 정확히 같은 회사."""
    hits = [c for c in corp_codes() if c["corp_name"] == name and c["stock_code"]]
    if not hits:
        raise DartError(f"상장사 '{name}'을 찾지 못했습니다")
    return hits[0]


def list_filings(corp_code, bgn_de, end_de=None, kind="A", page_count=100):
    """공시 목록. kind A = 정기공시(사업·반기·분기보고서)."""
    p = {"corp_code": corp_code, "bgn_de": bgn_de, "pblntf_ty": kind, "page_count": page_count}
    if end_de:
        p["end_de"] = end_de
    return _json("list.json", **p).get("list", [])


def annual_reports(corp_code, years):
    """사업보고서(12월 결산) 접수번호. 정정보고서가 있으면 가장 마지막 것을 쓴다."""
    out = {}
    for y in years:
        rows = list_filings(corp_code, f"{y + 1}0101", f"{y + 1}1231")
        rows = [r for r in rows if r["report_nm"].strip().endswith(f"사업보고서 ({y}.12)")]
        if rows:
            out[y] = max(rows, key=lambda r: r["rcept_no"])
    return out


def document(rcept_no):
    """공시 원문 ZIP을 받아 data/raw/<rcept_no>/에 풀고, 본문 XML 경로를 돌려준다."""
    d = RAW / rcept_no
    main = d / f"{rcept_no}.xml"
    if not main.exists():
        d.mkdir(parents=True, exist_ok=True)
        zipfile.ZipFile(io.BytesIO(_get("document.xml", rcept_no=rcept_no))).extractall(d)
    return main


def financials(corp_code, year, fs_div="CFS", reprt_code="11011"):
    """단일회사 전체 재무제표(XBRL 기반). reprt_code 11011 = 사업보고서, CFS = 연결."""
    cache = RAW / f"fin_{corp_code}_{year}_{fs_div}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    rows = _json("fnlttSinglAcntAll.json", corp_code=corp_code, bsns_year=year, reprt_code=reprt_code, fs_div=fs_div).get("list", [])
    cache.write_text(json.dumps(rows, ensure_ascii=False))
    return rows
