import { useEffect, useState } from "react";

interface Run {
  name: string;
  date: string;
  n: number;
  pass_rate: number;
  tokens: number;
  cost_usd: number;
  cost_per_q: number;
  p50_s: number;
  p95_s: number;
  cite_verified?: number | null;
  by_type?: Record<string, string>;
}
interface Ret {
  method: string;
  filter: boolean;
  para: boolean;
  ctx: boolean;
  recall5: number;
  mrr10: number;
  n: number;
}

const METHODS = ["keyword", "vector", "hybrid", "rerank"];
const LABEL: Record<string, string> = { keyword: "키워드(BM25)", vector: "벡터", hybrid: "하이브리드", rerank: "하이브리드+재정렬" };
const COLS = [
  { key: "base", label: "원래 질문", para: false, ctx: false },
  { key: "ctx", label: "+맥락", para: false, ctx: true },
  { key: "para", label: "말 바꾼 질문", para: true, ctx: false },
  { key: "para-ctx", label: "말 바꾼 질문 +맥락", para: true, ctx: true },
];

export default function Scorecard() {
  const [data, setData] = useState<{ runs: Run[]; retrieval: Ret[] } | null>(null);
  useEffect(() => {
    fetch("/api/scorecard").then((r) => r.json()).then(setData);
  }, []);
  if (!data) return <section className="card">불러오는 중…</section>;

  const last = data.runs[data.runs.length - 1];
  const cell = (m: string, para: boolean, ctx: boolean) =>
    data.retrieval.find((r) => r.method === m && r.filter && r.para === para && r.ctx === ctx);

  return (
    <>
      <section className="card">
        <h2>답변 성적표 (질문 → 검색 → 답변 전체)</h2>
        <table className="score">
          <thead>
            <tr>
              <th>실행</th><th>통과율</th><th>인용 검증</th><th>문항</th><th>토큰</th><th>$/문항</th><th>p50 / p95</th><th>시각</th>
            </tr>
          </thead>
          <tbody>
            {data.runs.map((r, i) => (
              <tr key={i}>
                <td>{r.name}</td>
                <td><Meter v={r.pass_rate} /></td>
                <td>{r.cite_verified != null ? `${Math.round(r.cite_verified * 100)}%` : "–"}</td>
                <td>{r.n}</td>
                <td>{r.tokens.toLocaleString()}</td>
                <td>${r.cost_per_q.toFixed(4)}</td>
                <td>{r.p50_s}s / {r.p95_s}s</td>
                <td className="muted">{r.date}</td>
              </tr>
            ))}
            {data.runs.length === 0 && (
              <tr><td colSpan={8} className="muted">아직 실행 기록이 없습니다: python -m dart_rag.eval_answers</td></tr>
            )}
          </tbody>
        </table>
        {last?.by_type && (
          <div className="types">
            {Object.entries(last.by_type).map(([k, v]) => (
              <span key={k} className="chip static">{k} {v}</span>
            ))}
          </div>
        )}
      </section>

      <section className="card">
        <h2>검색 성적표 — recall@5 (회사·연도 필터)</h2>
        <table className="score">
          <thead>
            <tr>
              <th>방식</th>
              {COLS.map((c) => <th key={c.key}>{c.label}</th>)}
            </tr>
          </thead>
          <tbody>
            {METHODS.map((m) => (
              <tr key={m}>
                <td>{LABEL[m]}</td>
                {COLS.map((c) => {
                  const v = cell(m, c.para, c.ctx);
                  return <td key={c.key}>{v ? <Meter v={v.recall5} sub={`MRR ${v.mrr10.toFixed(2)}`} /> : "–"}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}

function Meter({ v, sub }: { v: number; sub?: string }) {
  return (
    <div className="meter">
      <div className="meter-track"><div className="meter-fill" style={{ width: `${v * 100}%` }} /></div>
      <span className="meter-num">{v.toFixed(3)}</span>
      {sub && <span className="meter-sub">{sub}</span>}
    </div>
  );
}
