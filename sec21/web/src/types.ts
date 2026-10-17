// 20편 백엔드가 보내는 이벤트와 결과의 모양

export type Task = { id: string; worker: "filings" | "financials" | "news"; corp?: string; query: string };
export type Sentence = { sentence: string; cites: string[]; badge: string; reason: string };
export type Evidence = { id: string; source: string; claim: string; quote: string };
export type Company = { corp: string; year: number; rcept_no: string; url: string };
export type FinRow = { account: string; current: number; previous: number };

export type Lane = { task: Task; start: number; end?: number; n?: number; error?: string };
export type Done = { report: Sentence[]; evidence: Evidence[]; rounds: number; seconds: number; spent: number };

export type Status =
  | { kind: "idle" }
  | { kind: "running"; label: string }
  | { kind: "done"; result: Done }
  | { kind: "stopped"; message: string };
