# 21편 프론트엔드 — React로 진행 타임라인 · 인용 배지 보고서

## 파일
| 파일 | 내용 |
|---|---|
| `api.py` | 20편 서버(`sec20/server.py`의 app)를 가져와 API 두 개를 더한다: `/api/companies`(회사 · 접수번호 · DART 원문 주소), `/api/financials?corp=`(MCP `get_financials` → 차트용 숫자) |
| `web/vite.config.ts` | `/api` 요청을 8790 백엔드로 넘기는 프록시(브라우저에겐 같은 주소 → CORS 설정 불필요) |
| `web/src/useResearch.ts` | EventSource로 SSE를 열고, 이벤트(plan · task_start/end · writing · verify · revise · done · budget/error)를 화면 상태로 바꾸는 훅 |
| `web/src/Timeline.tsx` | 작업마다 진행 막대(진행 중은 노란색, 끝나면 초록) |
| `web/src/Report.tsx` | 문장마다 심판 배지 + 근거 번호 버튼 → 원문 인용 · 출처 · DART 원문 링크 |
| `web/src/FinChart.tsx` | 매출액 · 영업이익 · 당기순이익 전기 vs 당기 막대(SVG, 라이브러리 없음) |
| `web/src/solutions/` | 과제 풀이 |

## 실행
```bash
uv run uvicorn api:app --app-dir sec21 --port 8790 > data/server21.log 2>&1 &
npm --prefix sec21/web install
npm --prefix sec21/web run dev < /dev/null &   # 백그라운드에서 키 입력을 기다리며 멈추지 않게
# 브라우저: http://localhost:5173/
```
- React 19.1 · Vite 6.3 · TypeScript 5.8(버전 고정, `package.json`).

## 실제 결과 (2026-10-17 강의 녹화 실행, 모델 deepseek-v4-flash)
- 삼성전자 "2025년 실적과 사업 위험 요인을 정리해 줘": 재무 근거 3(2.2초) · 공시 근거 4(49.5초) → 심판 1차 5/6 → 반성 1회 → 2차 5/6. 130.3초 · $0.0011.
  - 남은 "부족" 1문장: 거래상대방 계약 불이행으로 인한 신용위험(근거 e4). 화면에서 주황 배지로 보인다.
  - 근거 e2 → "삼성전자 2025 사업보고서 · III. 재무에 관한 사항 > 28. 재무위험관리", DART 원문 링크.
  - 차트: 매출 300조 8,709억 → 333조 6,059억, 영업이익 32조 7,260억 → 43조 6,011억, 당기순이익 34조 4,514억 → 45조 2,068억.
- 개발 중 확인(카카오): 85.2초 · $0.0005 · 지지 6/6(반성 없음).

## 과제
1. 재무 차트 아래에 영업이익률(영업이익 ÷ 매출액)을 전기 · 당기로 보여 준다.
2. "지지"가 아닌 문장은 기본으로 접고 버튼으로 펼친다.
3. 끝난 리서치를 브라우저(localStorage)에 저장해 다시 돌리지 않고 연다.

풀이와 해설은 `SOLUTIONS.md`.
