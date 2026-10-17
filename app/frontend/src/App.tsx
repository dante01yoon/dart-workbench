import { useEffect, useRef, useState } from "react";
import type { Event, FinRow, Lane, Result, Task } from "./types";
import "./App.css";
import Scorecard from "./Scorecard";

const EXAMPLES = [
  "삼성전자와 SK하이닉스의 2025년 메모리 사업 실적과 위험 요인을 비교해 줘",
  "카카오의 2025년 영업이익과 주요 사업 부문을 알려줘",
  "현대자동차의 2025년 실적과 최근 관세 관련 뉴스를 같이 정리해 줘",
];
const WORKER_LABEL = { filings: "공시", financials: "재무", news: "뉴스" } as const;
const JO = 1e12;

type Phase = "idle" | "planning" | "working" | "writing" | "done" | "error";

export default function App() {
  const [q, setQ] = useState(EXAMPLES[0]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [lanes, setLanes] = useState<Record<string, Lane>>({});
  const [writing, setWriting] = useState<number | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [now, setNow] = useState(0);
  const [fin, setFin] = useState<FinRow[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [tab, setTab] = useState<"research" | "score">("research");
  const started = useRef(0);
  const es = useRef<EventSource | null>(null);

  useEffect(() => {
    fetch("/api/financials").then((r) => r.json()).then(setFin).catch(() => setFin([]));
  }, []);

  useEffect(() => {
    if (phase === "idle" || phase === "done" || phase === "error") return;
    const id = setInterval(() => setNow((Date.now() - started.current) / 1000), 100);
    return () => clearInterval(id);
  }, [phase]);

  function run() {
    es.current?.close();
    setLanes({});
    setResult(null);
    setError("");
    setWriting(null);
    setPhase("planning");
    started.current = Date.now();
    const src = new EventSource(`/api/research?q=${encodeURIComponent(q)}`);
    es.current = src;
    src.onmessage = (m) => {
      const e = JSON.parse(m.data) as Event;
      if (e.type === "plan") {
        setPhase("working");
        setLanes(Object.fromEntries(e.tasks.map((t: Task) => [t.id, { task: t, start: e.t }])));
      } else if (e.type === "task_start") {
        setLanes((l) => ({ ...l, [e.id]: { ...l[e.id], start: e.t } }));
      } else if (e.type === "task_end") {
        setLanes((l) => ({ ...l, [e.id]: { ...l[e.id], end: e.t, n: e.n, error: e.error, claims: e.claims } }));
      } else if (e.type === "writing") {
        setPhase("writing");
        setWriting(e.t);
      } else if (e.type === "done") {
        setResult(e);
        setPhase("done");
        src.close();
      } else if (e.type === "error") {
        setError(e.message);
        setPhase("error");
        src.close();
      }
    };
    src.onerror = () => {
      setError("서버 연결이 끊겼습니다.");
      setPhase("error");
      src.close();
    };
  }

  const busy = phase === "planning" || phase === "working" || phase === "writing";
  const total = Math.max(now, result?.seconds ?? 0, 10);
  const evidence = Object.fromEntries((result?.evidence ?? []).map((e) => [e.id, e]));

  return (
    <div className="page">
      <header>
        <h1>AI 투자 리서치 워크벤치</h1>
        <p className="sub">삼성전자 · SK하이닉스 · 현대자동차 · 카카오 — 2024·2025 사업보고서(DART)와 뉴스로 답합니다. 투자 권유가 아닙니다.</p>
        <nav className="tabs">
          <button className={tab === "research" ? "on" : ""} onClick={() => setTab("research")}>리서치</button>
          <button className={tab === "score" ? "on" : ""} onClick={() => setTab("score")}>성적표</button>
        </nav>
      </header>

      {tab === "score" && <Scorecard />}
      <div hidden={tab !== "research"}>
      <section className="ask">
        <textarea value={q} onChange={(e) => setQ(e.target.value)} rows={2} />
        <div className="row">
          <div className="chips">
            {EXAMPLES.map((x) => (
              <button key={x} className="chip" onClick={() => setQ(x)} disabled={busy}>
                {x.slice(0, 22)}…
              </button>
            ))}
          </div>
          <button className="go" onClick={run} disabled={busy || q.trim().length < 2}>
            {busy ? "리서치 중…" : "리서치 시작"}
          </button>
        </div>
      </section>

      {phase !== "idle" && (
        <section className="card">
          <div className="card-head">
            <h2>진행 상황</h2>
            <span className="muted">
              {phase === "planning" && "계획 세우는 중"}
              {phase === "working" && "근거 모으는 중"}
              {phase === "writing" && "보고서 쓰는 중"}
              {phase === "done" && `완료 · ${result?.seconds}s · ${result?.tokens?.toLocaleString()} 토큰 · 인용 검증 ${result?.quote_ok}`}
              {phase === "error" && error}
            </span>
          </div>
          <div className="gantt">
            {Object.values(lanes).map((l) => (
              <div className="lane" key={l.task.id}>
                <div className="lane-label">
                  <span className={`tag ${l.task.worker}`}>{WORKER_LABEL[l.task.worker]}</span>
                  <span className="lane-text">{[l.task.corp, l.task.query].filter(Boolean).join(" · ")}</span>
                </div>
                <div className="track">
                  <div
                    className={`bar ${l.task.worker} ${l.end === undefined ? "live" : ""} ${l.error ? "err" : ""}`}
                    style={{ left: `${(l.start / total) * 100}%`, width: `${(((l.end ?? now) - l.start) / total) * 100}%` }}
                  />
                </div>
                <div className="lane-n">{l.end !== undefined ? (l.error ? "오류" : `근거 ${l.n}`) : "…"}</div>
              </div>
            ))}
            {writing !== null && (
              <div className="lane">
                <div className="lane-label">
                  <span className="tag writer">작성</span>
                  <span className="lane-text">보고서</span>
                </div>
                <div className="track">
                  <div
                    className={`bar writer ${phase === "writing" ? "live" : ""}`}
                    style={{ left: `${(writing / total) * 100}%`, width: `${(((result?.seconds ?? now) - writing) / total) * 100}%` }}
                  />
                </div>
                <div className="lane-n" />
              </div>
            )}
          </div>
        </section>
      )}

      {result && !result.refused && (
        <section className="card">
          <h2>보고서</h2>
          <ol className="report">
            {result.report.map((s, i) => (
              <li key={i} className={s.badge}>
                <span>{s.sentence}</span>
                {s.cites.map((c) => (
                  <button key={c} className="cite" onClick={() => setOpen(open === c ? null : c)}>
                    {c}
                  </button>
                ))}
                {s.badge === "red" && <span className="nocite">근거 없음</span>}
                {s.cites.includes(open ?? "") && evidence[open!] && (
                  <blockquote>
                    <div className="src">{evidence[open!].source}</div>“{evidence[open!].quote}”
                  </blockquote>
                )}
              </li>
            ))}
          </ol>
        </section>
      )}
      {result?.refused && (
        <section className="card">
          <h2>답하지 않은 질문</h2>
          <p>투자 권유(매수·매도·목표가)는 하지 않습니다. 공시 내용을 묻는 질문으로 바꿔 주세요.</p>
        </section>
      )}

      {fin.length > 0 && <FinChart rows={fin} />}
      </div>
      <footer>출처: 금융감독원 전자공시(OpenDART). 숫자는 재무 API 기준이며 투자 판단의 근거가 아닙니다.</footer>
    </div>
  );
}

function FinChart({ rows }: { rows: FinRow[] }) {
  const corps = [...new Set(rows.map((r) => r.corp))];
  const max = Math.max(...rows.map((r) => r.영업이익 ?? 0));
  return (
    <section className="card">
      <h2>영업이익 (조 원, 재무 API)</h2>
      <div className="fin">
        {corps.map((c) => (
          <div key={c} className="fin-row">
            <div className="fin-corp">{c}</div>
            <div className="fin-bars">
              {[2024, 2025].map((y) => {
                const v = rows.find((r) => r.corp === c && r.year === y)?.영업이익 ?? 0;
                return (
                  <div key={y} className="fin-bar-wrap">
                    <div className={`fin-bar y${y}`} style={{ width: `${(Math.max(v, 0) / max) * 100}%` }} />
                    <span className="fin-val">
                      {y} · {(v / JO).toFixed(1)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
