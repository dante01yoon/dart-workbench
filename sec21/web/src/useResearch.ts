import { useRef, useState } from "react";
import type { Done, Lane, Status, Task } from "./types";

// SSE 연결 하나로 리서치 진행 이벤트를 받아 화면 상태로 바꾼다
export function useResearch() {
  const [lanes, setLanes] = useState<Record<string, Lane>>({});
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [log, setLog] = useState<string[]>([]);
  const [t0, setT0] = useState(0); // 서버의 t(초)와 맞추려고 시작 시각을 기억한다
  const src = useRef<EventSource | null>(null);

  function start(question: string) {
    src.current?.close();
    setLanes({});
    setLog([]);
    setT0(Date.now());
    setStatus({ kind: "running", label: "계획 세우는 중…" });
    const es = new EventSource(`/api/research?q=${encodeURIComponent(question)}`);
    src.current = es;
    const on = <T,>(type: string, fn: (e: T) => void) =>
      es.addEventListener(type, (m) => fn(JSON.parse((m as MessageEvent).data)));
    const note = (s: string) => setLog((l) => [...l, s]);

    on<{ tasks: Task[]; t: number }>("plan", (e) => {
      setLanes(Object.fromEntries(e.tasks.map((t) => [t.id, { task: t, start: e.t }])));
      setStatus({ kind: "running", label: `작업 ${e.tasks.length}개 진행 중…` });
    });
    on<{ id: string; t: number }>("task_start", (e) => setLanes((l) => ({ ...l, [e.id]: { ...l[e.id], start: e.t } })));
    on<{ id: string; t: number; n: number; error?: string }>("task_end", (e) =>
      setLanes((l) => ({ ...l, [e.id]: { ...l[e.id], end: e.t, n: e.n, error: e.error } })),
    );
    on<{ evidence: number }>("writing", (e) => setStatus({ kind: "running", label: `보고서 쓰는 중… (근거 ${e.evidence}개)` }));
    on<{ round: number; ok: number; total: number }>("verify", (e) => {
      note(`심판 ${e.round}차 · 지지 ${e.ok}/${e.total}`);
      setStatus({ kind: "running", label: `심판 ${e.round}차 확인 끝` });
    });
    on<{ bad: number }>("revise", (e) => {
      note(`반성 · 부족한 문장 ${e.bad}개 고쳐 쓰기`);
      setStatus({ kind: "running", label: "반성: 고쳐 쓰는 중…" });
    });
    on("revise_kept", () => note("반성 · 고친 답이 비어 원래 보고서 유지"));
    on<Done>("done", (e) => {
      setStatus({ kind: "done", result: e });
      es.close();
    });
    for (const k of ["budget", "error", "refused"]) {
      on<{ message?: string }>(k, (e) => {
        setStatus({ kind: "stopped", message: e.message ?? "투자 권유 질문은 답하지 않습니다" });
        es.close();
      });
    }
  }

  return { lanes, status, log, t0, start };
}
