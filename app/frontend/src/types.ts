export type Worker = "filings" | "financials" | "news";

export interface Task {
  id: string;
  worker: Worker;
  corp: string | null;
  year: number;
  query: string;
}

export interface Lane {
  task: Task;
  start: number;
  end?: number;
  n?: number;
  error?: string | null;
  claims?: string[];
}

export interface Evidence {
  id: string;
  claim: string;
  source: string;
  quote: string;
  kind: "filing" | "news" | "financials";
  verified: boolean;
}

export interface Sentence {
  sentence: string;
  cites: string[];
  badge: "green" | "red";
}

export interface Result {
  question: string;
  refused: boolean;
  report: Sentence[];
  evidence: Evidence[];
  seconds?: number;
  tokens?: number;
  quote_ok?: string;
}

export type Event =
  | { type: "planning"; t: number }
  | { type: "plan"; t: number; tasks: Task[] }
  | { type: "task_start"; id: string; t: number }
  | { type: "task_end"; id: string; t: number; n: number; error?: string | null; claims: string[] }
  | { type: "writing"; t: number; evidence: number; verified: number }
  | ({ type: "done" } & Result)
  | { type: "error"; message: string };

export interface FinRow {
  corp: string;
  year: number;
  매출액?: number;
  영업이익?: number;
  당기순이익?: number;
}
