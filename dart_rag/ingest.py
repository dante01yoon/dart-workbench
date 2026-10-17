"""사업보고서 본문 XML → 섹션 → 청크.

- 목차: <SECTION-n> 안의 <TITLE ATOC="Y">가 목차 항목이다(n이 깊이).
- 표: <TR> 하나를 "칸 | 칸 | 칸" 한 줄로 바꾼다. 청크를 나눌 때 표 머리 행을 다시 붙여 숫자가 무슨 열인지 잃지 않게 한다.
- 청크 메타데이터: 회사, 사업연도, 접수번호, 섹션 경로, 종류(text/table).
"""

import html
import json
import re
from pathlib import Path

TAG = re.compile(r"<(/?)(SECTION-(\d)|TITLE|TABLE|TR|P)\b([^>]*)>", re.S)
CELL = re.compile(r"<(TD|TH|TE|TU)\b[^>]*>(.*?)</\1>", re.S)


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def table_rows(tb):
    rows = []
    for tr in re.findall(r"<TR\b[^>]*>(.*?)</TR>", tb, re.S):
        cells = [clean(c) for _, c in CELL.findall(tr)]
        if any(cells):
            rows.append(" | ".join(cells))
    return rows


def sections(xml):
    """[(경로 리스트, 블록 리스트)] — 블록은 ("text", 문단) 또는 ("table", [행...])."""
    out, path, depth_stack = [], [], []
    titles = [(m.start(), m.end(), m.group(1)) for m in re.finditer(r'<TITLE ATOC="Y"[^>]*>(.*?)</TITLE>', xml, re.S)]
    for i, (s, e, title) in enumerate(titles):
        # 이 TITLE을 감싸는 SECTION 깊이 = 직전 SECTION 여는 태그
        opened = list(re.finditer(r"<SECTION-(\d)\b", xml[:s]))
        depth = int(opened[-1].group(1)) if opened else 1
        while depth_stack and depth_stack[-1] >= depth:
            depth_stack.pop()
            path.pop()
        depth_stack.append(depth)
        path.append(clean(title))
        body = xml[e : titles[i + 1][0] if i + 1 < len(titles) else len(xml)]
        blocks, pos = [], 0
        for m in re.finditer(r"<TABLE\b.*?</TABLE>", body, re.S):
            for p in re.findall(r"<P\b[^>]*>(.*?)</P>", body[pos : m.start()], re.S):
                if clean(p):
                    blocks.append(("text", clean(p)))
            rows = table_rows(m.group(0))
            if rows:
                blocks.append(("table", rows))
            pos = m.end()
        for p in re.findall(r"<P\b[^>]*>(.*?)</P>", body[pos:], re.S):
            if clean(p):
                blocks.append(("text", clean(p)))
        out.append((list(path), blocks))
    return out


def chunk(blocks, size=900):
    """블록을 size 자 안팎으로 묶는다.
    표는 바로 앞의 짧은 블록(기간·단위 같은 표 제목, 300자 이하)을 캡션으로 삼아
    나눈 조각마다 "캡션 + 머리 행"을 다시 붙인다. 그래야 숫자가 어느 기·어느 단위인지 잃지 않는다."""
    out, buf = [], []
    caption = ""

    def flush():
        nonlocal buf
        if buf:
            out.append(("text", "\n".join(buf)))
        buf = []

    for k, b in blocks:
        if k == "text":
            if sum(map(len, buf)) + len(b) > size:
                flush()
            buf.append(b)
            caption = b if len(b) <= 300 else ""
            continue
        text = "\n".join(b)
        if len(text) <= 300 and len(b) <= 6:
            # 작은 표: 그 자체로도 청크로 남기고(작은 데이터 표일 수 있음), 다음 표의 캡션으로도 쓴다(기간·단위)
            flush()
            out.append(("table", text))
            caption = text
            continue
        flush()
        head = ([caption] if caption else []) + [b[0]]
        part = list(head)
        for r in b[1:]:
            if sum(map(len, part)) + len(r) > size and len(part) > len(head):
                out.append(("table", "\n".join(part)))
                part = list(head)
            part.append(r)
        out.append(("table", "\n".join(part)))
        caption = ""
    flush()
    return out


def ingest(xml_path, corp, year, rcept_no):
    xml = Path(xml_path).read_text(encoding="utf-8", errors="ignore")
    rows = []
    for path, blocks in sections(xml):
        for j, (kind, text) in enumerate(chunk(blocks)):
            rows.append({
                "id": f"{rcept_no}-{len(rows):05d}",
                "corp": corp, "year": year, "rcept_no": rcept_no,
                "section": " > ".join(path), "kind": kind, "text": text,
            })
    return rows


if __name__ == "__main__":
    import sys

    rows = ingest(sys.argv[1], "test", 0, "x")
    print(len(rows), "chunks")
    print(json.dumps(rows[:2], ensure_ascii=False, indent=1))
