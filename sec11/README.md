# 11편 LangChain · LlamaIndex로 옮기기

## 파일
| 파일 | 내용 |
|---|---|
| `lc.py` | LangChain 버전: BM25Retriever(2글자 토큰을 preprocess_func로) · FAISS(7편 임베딩 그대로) · EnsembleRetriever(RRF) · 프롬프트 \| ChatOpenAI \| 문자열 |
| `li.py` | LlamaIndex 버전: TextNode(임베딩 미리) · VectorStoreIndex · BigramBM25(bm25s에 띄어 쓴 2글자 토큰) · QueryFusionRetriever(reciprocal_rerank) · OpenAILike |
| `01_langchain.py` | 질문 하나로 토크나이저 차이 · 하이브리드 상위 3 · 출처 답 + 10편 인용 확인 |
| `02_llamaindex.py` | 같은 시험을 LlamaIndex로 |
| `03_compare.py` | 직접 vs LangChain vs LlamaIndex: 38문항 × 원래 · 말 바꾼 질문, recall@5 · 검색 코드 줄 수 · 준비 시간 → `data/rag/frameworks.json` |
| `04_compare_web.py` | 비교 막대 화면 http://127.0.0.1:8811 |

## 실행
프레임워크 패키지는 선택 그룹이다. `uv run`만 쓰면 그룹이 빠지므로 `--group frameworks`를 붙인다.
```bash
uv sync --group frameworks
uv run --group frameworks python sec11/01_langchain.py
uv run --group frameworks python sec11/02_llamaindex.py
uv run --group frameworks python sec11/03_compare.py
uv run --group frameworks python sec11/04_compare_web.py
```
버전(녹화): langchain 1.4.4 · langchain-community 0.4.2(지원 종료 예정 경고) · langchain-classic 1.0.8 · llama-index-core 0.14.25 · llama-index-retrievers-bm25 0.8.0.

## 실제 결과 (2026-10-13 강의 녹화 실행, recall@5)
| | 키워드 | 벡터 | 하이브리드 | 기본 토크나이저 키워드 |
|---|---|---|---|---|
| 원래 · 직접 | 0.974 | 0.474 | 0.763 | - |
| 원래 · LangChain | 0.947 | 0.474 | 0.711 | 0.658 |
| 원래 · LlamaIndex | 0.974 | 0.474 | **0.842** | 0.737 |
| 말 바꿈 · 직접 | 0.789 | 0.395 | 0.684 | - |
| 말 바꿈 · LangChain | 0.816 | 0.395 | 0.632 | 0.368 |
| 말 바꿈 · LlamaIndex | **0.842** | 0.395 | 0.684 | 0.395 |

- 검색 코드 줄 수: 직접 42 · LangChain 43 · LlamaIndex 58. 한국어 2글자 토큰을 맞추느라 프레임워크로 옮겨도 줄지 않았다.
- 같은 임베딩을 넣었으니 벡터는 셋이 같다. 키워드 · 하이브리드는 라이브러리마다 BM25 계산식과 섞는 방식이 달라 점수가 다르다.
- 기본 토크나이저(띄어쓰기)는 한국어에서 크게 떨어진다. "현대자동차 사업부문별 매출 비중은?"은 기본으로 10위 안에 정답이 없고, 2글자 토큰으로 1위다.
- 부딪힌 점: OpenRouter 임베딩은 `check_embedding_ctx_length=False`가 필요, LangChain 1.x에서 EnsembleRetriever는 `langchain_classic`, LlamaIndex BM25는 tokenizer 인자를 무시(→ token_pattern + 미리 띄어 쓰기).

## 과제
1. LangChain EnsembleRetriever의 키워드 : 벡터 가중치를 바꿔 하이브리드를 잰다.
2. LlamaIndex QueryFusionRetriever의 mode를 순위 대신 점수 기반으로 바꾼다.
3. 10편 성적표(숫자 · 근거 없음 · 투자 권유)를 LangChain 체인으로 다시 돌린다.

풀이: [SOLUTIONS.md](SOLUTIONS.md)
