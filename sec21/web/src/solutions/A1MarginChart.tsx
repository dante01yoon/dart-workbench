// 과제 1 풀이: 재무 차트 아래에 영업이익률(영업이익 ÷ 매출액)을 전기 · 당기로 보여 준다.
// 사용: App.tsx에서 <FinChart …/> 다음 줄에 <A1Margin rows={fin} />
import type { FinRow } from "../types";

export default function A1Margin({ rows }: { rows: FinRow[] }) {
  const sales = rows.find((r) => r.account === "매출액");
  const op = rows.find((r) => r.account === "영업이익");
  if (!sales || !op) return null;
  const pct = (a: number, b: number) => (b === 0 ? "-" : `${((a / b) * 100).toFixed(1)}%`);
  return (
    <p className="note">
      영업이익률 2024 {pct(op.previous, sales.previous)} → 2025 {pct(op.current, sales.current)}
    </p>
  );
}
