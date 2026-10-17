import { useEffect, useState } from "react";
import type { Lane } from "./types";

const WORKER = { filings: "공시", financials: "재무", news: "뉴스" } as const;

// 작업마다 막대: 시작~끝(진행 중이면 지금까지). 가로축은 가장 늦은 시각에 맞춘다
export default function Timeline({ lanes, running, t0 }: { lanes: Record<string, Lane>; running: boolean; t0: number }) {
  const [now, setNow] = useState(0);
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setNow((Date.now() - t0) / 1000), 200);
    return () => clearInterval(id);
  }, [running, t0]);

  const rows = Object.values(lanes);
  if (rows.length === 0) return null;
  const max = Math.max(10, now, ...rows.map((r) => r.end ?? now));
  return (
    <section className="card">
      <h2>진행 타임라인</h2>
      {rows.map(({ task, start, end, n, error }) => {
        const stop = end ?? Math.max(now, start);
        return (
          <div className="lane" key={task.id}>
            <div className="lane-label">
              <b>{WORKER[task.worker]}</b> {task.corp ?? ""}
              <small>{task.query}</small>
            </div>
            <div className="track">
              <div
                className={`bar ${end == null ? "live" : error ? "fail" : "done"}`}
                style={{ left: `${(start / max) * 100}%`, width: `${Math.max(1, ((stop - start) / max) * 100)}%` }}
              />
            </div>
            <div className="lane-n">{end == null ? `${(stop - start).toFixed(0)}초…` : `근거 ${n} · ${(end - start).toFixed(1)}초`}</div>
          </div>
        );
      })}
    </section>
  );
}
