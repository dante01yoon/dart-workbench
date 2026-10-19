# 밑바닥부터 만드는 AI 에이전트 — 실전 실습 저장소 (RAG · 멀티 에이전트 · MCP)

금융감독원 전자공시(DART)의 실제 사업보고서로 **AI 투자 리서치 워크벤치**를 처음부터 만듭니다.
RAG · 멀티 에이전트 · MCP를 프레임워크 없이 직접 구현하고, 같은 성적표로 잰 뒤 LangChain · LlamaIndex · LangGraph로 옮겨 비교합니다.

> 이 저장소에는 공시 원문이 들어 있지 않습니다. 원문은 각자 발급한 OpenDART 키로 수집 스크립트를 실행해 받습니다.
> 결과는 투자 권유가 아니며, 숫자는 반드시 공시 원문으로 확인하세요.

## 시작하기 (0편)
```bash
uv sync
cp -n .env.example .env      # DART_API_KEY · OPENAI_API_KEY(OpenRouter 키) · TAVILY_API_KEY 채우기
uv run python check_setup.py # 11/11 통과 — 준비 완료!
```

| 키 | 발급 | 메모 |
|---|---|---|
| OpenRouter | https://openrouter.ai → Keys | `OPENAI_API_KEY` 칸에 넣습니다(OpenAI 호환 API) |
| OpenDART | https://opendart.fss.or.kr → 인증키 신청 | 무료 · 1인 1키 · 공유 금지 · 키는 "오픈API 이용현황"에서 확인 |
| Tavily | https://app.tavily.com → API Keys | 무료 플랜 월 1,000크레딧 |

## 데이터 받기 (섹션 2·4)
```bash
uv run python -m dart_rag.collect      # 4개사 × 2개년 사업보고서 + 재무 API → data/ (약 10분)
uv run python eval/make_questions.py   # 평가 세트 60문항 + 정답 근거 존재 확인
```

## 폴더
| 폴더 | 섹션 | 내용 |
|---|---|---|
| `dart_rag/` | 1~5 | OpenDART 클라이언트, 수집·청킹, 검색(BM25·벡터·하이브리드·재정렬), 답변·인용 검증, 하네스·성적표, 리서치 팀 |
| `eval/` | 1·4·8 | 평가 문항과 채점 기준 · 시험지 v2(`questions_v2.jsonl`, 25편) |
| `skills/` | 3 | SKILL.md 예제 8개 |
| `mcp_server/` | 6 | 손으로 만든 MCP 서버 · 공식 SDK 버전 · 원격(HTTP + 토큰) |
| `frameworks/` | 4·5·6 | LangChain · LlamaIndex · LangGraph · MCP 어댑터로 옮긴 버전 |
| `app/` | 7 | 워크벤치: FastAPI 백엔드 + React·TypeScript 프론트 |
| `sec23`~ | 8 | AI 평가: 평가 대상 지도 · 공개 벤치마크와 오염 검사 · 실행 기록에서 시험지 v2 만들기 · 오류 분석 · 루브릭 · 코드 채점기와 실행 기반 채점(편마다 README · SOLUTIONS) |

프레임워크 비교(11·14편)는 `uv sync --group frameworks`로 추가 패키지를 설치합니다.
