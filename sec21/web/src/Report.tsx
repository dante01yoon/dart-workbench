import { useState } from "react";
import type { Company, Done } from "./types";

const BADGE: Record<string, string> = { 지지: "ok", 부족: "part", "출처 없음": "bad" };

// 문장마다 심판 배지 + 근거 번호. 번호를 누르면 원문 인용과 DART 원문 링크를 펼친다
export default function Report({ result, company }: { result: Done; company?: Company }) {
  const [open, setOpen] = useState<string | null>(null);
  const ev = Object.fromEntries(result.evidence.map((e) => [e.id, e]));
  const ok = result.report.filter((s) => s.badge === "지지").length;
  return (
    <section className="card">
      <h2>
        보고서 <span className="meta">지지 {ok}/{result.report.length} · 반성 {result.rounds}회 · {result.seconds}초 · ${result.spent}</span>
      </h2>
      {result.report.map((s, i) => (
        <div className="sent" key={i}>
          <span className={`badge ${BADGE[s.badge] ?? "part"}`} title={s.reason}>
            {s.badge}
          </span>
          <span>{s.sentence}</span>
          {s.cites.map((c) => (
            <button key={c} className={`cite ${open === c ? "on" : ""}`} onClick={() => setOpen(open === c ? null : c)}>
              {c}
            </button>
          ))}
          {s.cites.includes(open ?? "") && ev[open!] && (
            <div className="quote">
              <div className="src">{ev[open!].source}</div>
              <q>{ev[open!].quote}</q>
              {company && ev[open!].source.includes("사업보고서") && (
                <a href={company.url} target="_blank" rel="noreferrer">
                  DART 원문 보기 ↗
                </a>
              )}
            </div>
          )}
        </div>
      ))}
      <p className="note">투자 권유가 아닙니다. 숫자는 반드시 공시 원문으로 확인하세요.</p>
    </section>
  );
}
