# 1편 에이전트 루프 복습과 성적표 첫 줄

## 파일
| 파일 | 내용 |
|---|---|
| `tools.py` | 도구 `get_financials(corp, year)` — OpenDART 재무 API로 연결 손익(매출액·영업이익·당기순이익, 원). 모델에게 보여 줄 도구 설명 `TOOLS` |
| `01_loop.py` | 에이전트 루프를 HTTP 요청만으로 (OpenRouter, OpenAI 호환 형식) |
| `02_sdk.py` | 같은 루프를 OpenAI 공식 SDK로 — `base_url`만 OpenRouter |
| `03_harness.py` | 하네스: 숫자 문항 12개를 돌려 통과율·토큰·문항당 비용·p50/p95 지연을 `data/scorecard.jsonl`에 한 줄로 |
| `scoreboard.py` | 성적표 웹 화면 http://127.0.0.1:8800 |

## 실행
```bash
uv run python sec01/01_loop.py "SK하이닉스의 2025년 영업이익은 얼마야?"
uv run python sec01/02_sdk.py
uv run python sec01/03_harness.py
uv run python sec01/scoreboard.py
```

## 에이전트 루프 한 번 더
1. 대화 기록 + 도구 설명을 모델에게 보낸다
2. 모델이 바로 답하거나(`tool_calls` 없음) 도구를 요청한다
3. 도구 요청이면 우리 코드가 실행하고, 결과를 `role: tool` 메시지로 붙인다 (실패도 에러 메시지로 돌려준다)
4. 1로 돌아간다. 도구 요청이 없으면 그 답이 최종 답

Anthropic 형식은 `system`을 따로 넣고, 도구 요청·결과가 `tool_use`·`tool_result` 블록으로 들어간다. 이름만 다르고 루프는 같다.

## 성적표의 네 칸
- **통과율**: 정답이 정해진 질문 세트에서 맞힌 비율. 1편 세트는 숫자 문항 12개, 정답은 재무 API 값
- **토큰**: 모델이 읽고 쓴 양
- **문항당 비용**: OpenRouter `usage: {"include": true}`가 돌려주는 실제 비용(달러)
- **지연 p50 · p95**: 중간값과 느린 쪽 5%. 사용자가 답답함을 느끼는 건 p95

## 녹화 때 실제 결과 (2026-10-11, deepseek-v4-pro)
12/12 통과 · 14,839 토큰 · 문항당 $0.00019 · p50 19.7초 · p95 27.5초

## 과제
1. `MODEL=anthropic/claude-haiku-5.5`로 바꿔 돌리고 두 줄을 비교한다.
2. 연도 비교 문항을 더한다: `uv run python sec01/03_harness.py "과제2" number,year_compare`. 떨어지는 문항이 왜 떨어지는지 찾는다.
3. 도구 설명을 `"데이터"` 한 단어로 바꾸고, 통과율 말고 무엇이 변하는지 성적표로 확인한다.

풀이: [SOLUTIONS.md](SOLUTIONS.md)
