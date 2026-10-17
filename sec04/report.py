"""4편 사업보고서 원문 받기: 공시 목록에서 사업보고서 접수번호를 찾고, 원문 ZIP(document.xml)을 받아 목차 단위로 나눈다.

- 목차: <TITLE ATOC="Y">가 목차 항목, 감싸는 <SECTION-n>의 n이 깊이다.
- 표: <TR> 한 줄을 "칸 | 칸 | 칸" 한 줄 글로 바꾼다.
- 결과는 data/reports/<회사>_<연도>.json 에 저장해 두고 다시 쓴다(원문 ZIP은 수 MB).
사용: uv run python sec04/report.py 카카오 2025
"""

import html
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sec02"))
from tools15 import CORP_CODE, ROOT

CACHE = ROOT / "data" / "reports"


def _get(endpoint, **params):
    params["crtfc_key"] = os.environ["DART_API_KEY"]
    url = f"https://opendart.fss.or.kr/api/{endpoint}?{urllib.parse.urlencode(params)}"
    return urllib.request.urlopen(url, timeout=120).read()


def rcept_no(corp, year):
    """그 연도 사업보고서의 접수번호. 정정 보고서가 있으면 가장 마지막 것."""
    d = json.loads(
        _get(
            "list.json",
            corp_code=CORP_CODE[corp],
            bgn_de=f"{year + 1}0101",
            end_de=f"{year + 1}1231",
            pblntf_ty="A",
            page_count=100,
        )
    )
    rows = [r for r in d.get("list", []) if r["report_nm"].strip().endswith(f"사업보고서 ({year}.12)")]
    return max(rows, key=lambda r: r["rcept_no"])["rcept_no"]


def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def to_text(body):
    """섹션 본문 XML → 글. 문단은 한 줄, 표는 행마다 한 줄."""
    lines = []
    for m in re.finditer(r"<TABLE\b.*?</TABLE>|<P\b[^>]*>.*?</P>", body, re.DOTALL):
        if m.group(0).startswith("<TABLE"):
            for tr in re.findall(r"<TR\b[^>]*>(.*?)</TR>", m.group(0), re.DOTALL):
                cells = [clean(c) for _, c in re.findall(r"<(TD|TH|TE|TU)\b[^>]*>(.*?)</\1>", tr, re.DOTALL)]
                if any(cells):
                    lines.append(" | ".join(cells))
        elif clean(m.group(0)):
            lines.append(clean(m.group(0)))
    return "\n".join(lines)


def sections(xml):
    """[{"no", "title"(상위 > 하위), "text"}] 목차 순서대로."""
    titles = list(re.finditer(r'<TITLE ATOC="Y"[^>]*>(.*?)</TITLE>', xml, re.DOTALL))
    out, path = [], []
    for i, t in enumerate(titles):
        opened = list(re.finditer(r"<SECTION-(\d)\b", xml[: t.start()]))
        depth = int(opened[-1].group(1)) if opened else 1
        path = path[: depth - 1] + [clean(t.group(1))]
        end = titles[i + 1].start() if i + 1 < len(titles) else len(xml)
        out.append({"no": i + 1, "title": " > ".join(path), "text": to_text(xml[t.end() : end])})
    return out


def load(corp, year):
    path = CACHE / f"{corp}_{year}.json"
    if path.exists():
        return json.loads(path.read_text())
    no = rcept_no(corp, year)
    z = zipfile.ZipFile(io.BytesIO(_get("document.xml", rcept_no=no)))
    main = next(n for n in z.namelist() if n == f"{no}.xml")  # 본문(나머지는 감사보고서 등 첨부)
    rep = {
        "corp": corp,
        "year": year,
        "rcept_no": no,
        "sections": sections(z.read(main).decode("utf-8", "ignore")),
    }
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rep, ensure_ascii=False))
    return rep


if __name__ == "__main__":
    corp, year = (sys.argv[1], int(sys.argv[2])) if len(sys.argv) > 2 else ("카카오", 2025)
    rep = load(corp, year)
    total = sum(len(s["text"]) for s in rep["sections"])
    print(
        f"{corp} {year} 사업보고서 · 접수번호 {rep['rcept_no']} · 목차 {len(rep['sections'])}개 · 본문 {total:,}자"
    )
    for s in sorted(rep["sections"], key=lambda s: -len(s["text"]))[:8]:
        print(f"  {len(s['text']):8,}자  [{s['no']:3d}] {s['title'][:60]}")
