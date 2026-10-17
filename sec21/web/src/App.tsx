import { useEffect, useState } from "react";
import FinChart from "./FinChart";
import Report from "./Report";
import Timeline from "./Timeline";
import type { Company, FinRow } from "./types";
import { useResearch } from "./useResearch";

const ASK = ["2025년 실적과 사업 위험 요인을 정리해 줘", "2025년 영업이익과 주요 사업 부문을 알려줘"];

export default function App() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [corp, setCorp] = useState("카카오");
  const [q, setQ] = useState(`카카오 ${ASK[0]}`);
  const [fin, setFin] = useState<FinRow[]>([]);
  const { lanes, status, log, t0, start } = useResearch();
  const running = status.kind === "running";

  useEffect(() => {
    fetch("/api/companies").then((r) => r.json()).then(setCompanies);
  }, []);
  useEffect(() => {
    setFin([]);
    fetch(`/api/financials?corp=${encodeURIComponent(corp)}`).then((r) => (r.ok ? r.json() : [])).then(setFin);
  }, [corp]);

  function pick(c: string) {
    setCorp(c);
    setQ(`${c} ${ASK[0]}`);
  }

  return (
    <main>
      <header>
        <h1>AI 투자 리서치 워크벤치</h1>
        <p>2025 사업보고서 · 리서치 팀 + 공시 MCP 서버 + 인용 심판</p>
      </header>

      <section className="card">
        <div className="corps">
          {companies.map((c) => (
            <button key={c.corp} className={c.corp === corp ? "corp on" : "corp"} onClick={() => pick(c.corp)} disabled={running}>
              {c.corp}
            </button>
          ))}
        </div>
        <form
          className="ask"
          onSubmit={(e) => {
            e.preventDefault();
            start(q);
          }}
        >
          <input value={q} onChange={(e) => setQ(e.target.value)} disabled={running} />
          <button disabled={running || q.trim().length < 2}>{running ? "리서치 중…" : "리서치 시작"}</button>
        </form>
        <div className={`status ${status.kind}`}>
          {status.kind === "idle" && "회사를 고르고 질문하세요."}
          {status.kind === "running" && status.label}
          {status.kind === "done" && "완료"}
          {status.kind === "stopped" && `멈춤 · ${status.message}`}
          {log.map((l) => (
            <span key={l} className="log">
              {l}
            </span>
          ))}
        </div>
      </section>

      <div className="grid">
        <div>
          <Timeline lanes={lanes} running={running} t0={t0} />
          {status.kind === "done" && <Report result={status.result} company={companies.find((c) => c.corp === corp)} />}
        </div>
        <FinChart corp={corp} rows={fin} />
      </div>
    </main>
  );
}
