// 과제 2 풀이: "지지"가 아닌 문장은 기본으로 접고, 버튼으로 펼친다. 심판을 통과한 문장만 먼저 읽게 한다.
import { useState } from "react";
import type { Sentence } from "../types";

export default function A2Collapse({ report }: { report: Sentence[] }) {
  const [show, setShow] = useState(false);
  const ok = report.filter((s) => s.badge === "지지");
  const weak = report.filter((s) => s.badge !== "지지");
  return (
    <div>
      {ok.map((s, i) => (
        <div className="sent" key={i}>
          <span className="badge ok">지지</span>
          {s.sentence}
        </div>
      ))}
      {weak.length > 0 && (
        <button className="cite" onClick={() => setShow(!show)}>
          {show ? "접기" : `근거가 약한 문장 ${weak.length}개 보기`}
        </button>
      )}
      {show &&
        weak.map((s, i) => (
          <div className="sent" key={i}>
            <span className="badge part" title={s.reason}>
              {s.badge}
            </span>
            {s.sentence}
          </div>
        ))}
    </div>
  );
}
