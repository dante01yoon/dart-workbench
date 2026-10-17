import type { FinRow } from "./types";

const EOK = 1e8; // 억 원

// 매출액 · 영업이익 · 당기순이익을 전기 vs 당기 막대로. 차트 라이브러리 없이 SVG로 그린다
export default function FinChart({ corp, rows }: { corp: string; rows: FinRow[] }) {
  if (rows.length === 0) return null;
  const max = Math.max(...rows.flatMap((r) => [Math.abs(r.current), Math.abs(r.previous)]));
  const W = 520, rowH = 64, barH = 20, x0 = 110, w = W - x0 - 120;
  const len = (v: number) => Math.max(2, (Math.abs(v) / max) * w);
  const fmt = (v: number) => `${Math.round(v / EOK).toLocaleString()}억`;
  return (
    <section className="card">
      <h2>
        {corp} 재무 <span className="meta">MCP get_financials · 연결 · 원 단위를 억으로</span>
      </h2>
      <svg viewBox={`0 0 ${W} ${rows.length * rowH + 10}`} className="chart">
        {rows.map((r, i) => {
          const y = i * rowH + 8;
          return (
            <g key={r.account}>
              <text x={0} y={y + barH + 4} className="acc">{r.account}</text>
              <rect x={x0} y={y} width={len(r.previous)} height={barH} className={r.previous < 0 ? "neg" : "prev"} />
              <text x={x0 + len(r.previous) + 6} y={y + 15} className="val">2024 {fmt(r.previous)}</text>
              <rect x={x0} y={y + barH + 4} width={len(r.current)} height={barH} className={r.current < 0 ? "neg" : "cur"} />
              <text x={x0 + len(r.current) + 6} y={y + barH + 19} className="val">2025 {fmt(r.current)}</text>
            </g>
          );
        })}
      </svg>
    </section>
  );
}
