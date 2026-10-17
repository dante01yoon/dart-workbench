"""11편 ① LangChain으로 옮긴 검색 · 답 시험: 질문 하나로 토크나이저 차이, 하이브리드 상위 3개, LCEL 답과 10편 인용 확인.
사용: uv run --group frameworks python sec11/01_langchain.py"""

import time
import warnings

warnings.filterwarnings("ignore")  # langchain-community 지원 종료 예정 경고
t0 = time.time()
import lc

print(f"LangChain 준비 {time.time() - t0:.1f}초 · 문서 {len(lc.DOCS):,}개 (FAISS에 7편 임베딩 그대로)")
from cite import check_sentence, sentences
from search import bigrams, eval_questions, first_hit

q = next(x for x in eval_questions() if x["id"] == "q18")  # 현대자동차 사업부문별 매출 비중
print(f"\n질문: {q['q']}")
print(f"  띄어쓰기 토큰: {q['q'].split()[:4]}")
print(f"  2글자 토큰:   {bigrams(q['q'])[:8]}")
for korean in (False, True):
    hit = first_hit(lc.CHUNKS, lc.search(q["q"], "keyword", q["corp"], korean), q)
    print(
        f"  BM25 {'2글자' if korean else '기본'} 토크나이저 → 정답 {'없음' if hit is None else f'{hit + 1}위'}"
    )
print("\n하이브리드(EnsembleRetriever) 상위 3개")
for r, i in enumerate(lc.search(q["q"], "hybrid", q["corp"], k=3), 1):
    print(f"  {r}. {lc.CHUNKS[i]['section'][-40:]}")
text, hits = lc.answer(q["q"], q["corp"])
print("\n답(프롬프트 | ChatOpenAI | 문자열)")
for s in sentences(text):
    print(f"  [{check_sentence(s, lc.CHUNKS, hits)}] {s}")
