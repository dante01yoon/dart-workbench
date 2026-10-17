// 과제 3 풀이: 끝난 리서치를 브라우저(localStorage)에 남겨 두고, 다시 돌리지 않고 열어 본다(비용 0).
// 사용: done 이벤트에서 saveRun(question, result), 화면에서 loadRuns()로 목록을 그린다.
import type { Done } from "../types";

const KEY = "workbench-runs";
export type Run = { question: string; at: string; result: Done };

export function loadRuns(): Run[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "[]");
  } catch {
    return []; // 사생활 보호 모드 등에서 저장소를 못 쓰면 빈 목록
  }
}

export function saveRun(question: string, result: Done) {
  const runs = [{ question, at: new Date().toISOString(), result }, ...loadRuns()].slice(0, 10); // 최근 10개만
  try {
    localStorage.setItem(KEY, JSON.stringify(runs));
  } catch {
    /* 저장 못 해도 화면은 그대로 */
  }
  return runs;
}
