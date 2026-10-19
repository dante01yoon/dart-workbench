# 33편 회귀 관문과 운영 — CI · 오프라인 vs 온라인 · 대시보드 · Langfuse로 옮겨 비교

면접 질문 "오프라인 점수는 올랐는데 운영 지표가 떨어졌다면?"과 "CI에서 평가로 무엇을 막나요?"에 답합니다. 26편 실행 53문항의 **저장된 모델 출력**을 PR마다 지금 코드로 다시 채점하는 회귀 관문을 GitHub Actions에 붙이고(모델 호출 0 · 비밀 값 0), 실제 PR이 막혔다가 통과하는 것까지 봅니다. 운영 트래픽은 없어서 26편 기록을 운영 로그라고 치고 "정답 없이 볼 수 있는 신호"를 잽니다. 마지막으로 같은 평가를 로컬 Langfuse에 옮겨 비교합니다.

## 파일
| 파일 | 내용 |
|---|---|
| `answer.py` | 최종 답 만들기(보고서 문장 + 근거 카드 요약 → 답 글). PR이 바꾸는 제품 코드 |
| `regress.py` | 공용: 저장된 실행 읽기 · 지금 코드로 다시 채점(28편 채점기 v3) · 기준 점수 |
| `00_freeze.py` | 26편 기록 → `runs/main.jsonl`(모델 출력만, 공시 원문 인용 없음) · 회귀/능력 세트 나누기 · `runs/baseline.json` (로컬, `data/` 필요) |
| `01_gate.py` | 회귀 관문: 회귀 세트 한 문항이라도 떨어지면 exit 1. GitHub에서는 떨어진 문항마다 오류 표시 + 실행 요약 표 |
| `../.github/workflows/eval-gate.yml` | PR · main 푸시마다 `python3 sec33/01_gate.py` (secrets 없음) |
| `02_online.py` | 오프라인 vs 온라인: 정답 없이 셀 수 있는 신호(빈 답 · 판사 부족 · 반성 · 느림 · 비쌈)가 오프라인 정답과 얼마나 맞나 · 표본 크기 |
| `03_dashboard.py` | 평가 대시보드 → http://127.0.0.1:8842 (실행별 관문 결과 · 문항 격자 · 운영 신호) |
| `04_langfuse.py` | 같은 평가를 로컬 Langfuse v2에: 데이터셋 · 실행 · 점수 올리고 다시 읽어 비교(다시 돌려도 중복 없음 — 첫 녹화에서 실행 연결이 106개로 쌓여 고침) |
| `langfuse/docker-compose.yml` | Langfuse v2 + Postgres, 127.0.0.1:3300, 가입 없이 프로젝트 · 키 생성 |
| `solutions/` | 과제 풀이(SOLUTIONS.md) |

## 실행
```bash
uv run python sec33/00_freeze.py      # (이미 runs/에 있음) 26편 기록에서 다시 만들 때만
python3 sec33/01_gate.py              # CI와 같은 명령 — 표준 라이브러리만, 몇 초
uv run python sec33/02_online.py
uv run python sec33/03_dashboard.py   # 01_gate.py --log data/gate33_runs.jsonl --label 이름 으로 쌓은 기록을 보여 준다
# Langfuse: .env에 LANGFUSE_PUBLIC_KEY=pk-lf-아무값 · LANGFUSE_SECRET_KEY=sk-lf-아무값(이 컴퓨터 안 시험용)을 적고
docker compose -p lf33 --env-file .env -f sec33/langfuse/docker-compose.yml up -d
uv run --with "langfuse>=2.60,<3" python sec33/04_langfuse.py
docker compose -p lf33 -f sec33/langfuse/docker-compose.yml down -v   # 끝나면 지우기
```

## 실제 결과 (2026-10-19)
- **회귀 · 능력 세트**(Anthropic "Demystifying evals": 능력 평가는 낮은 통과율에서 시작하는 언덕, 회귀 평가는 거의 100%여야): 26편 53문항 중 맞은 41개에서 10/18 세 번 돌리기에서 흔들린 6개(q44 q45 q47 q49 q56 q59)를 빼 **회귀 세트 35**, 나머지 **능력 세트 18**(지금 6/18). 세 번 기록이 없는 문항은 한 번만 보고 넣었다(한계).
- **CI 관문 — 실제 PR** [dante01yoon/dart-workbench#1](https://github.com/dante01yoon/dart-workbench/pull/1): 1차 커밋 d81103b "모바일 카드: 답을 앞 두 문장으로" → eval-gate **실패**(회귀 30/35, 떨어진 n11 n13 n16 n17 n18, 전체 77.4 → 67.9% · −9.4%p) · [실행 기록](https://github.com/dante01yoon/dart-workbench/actions/runs/39269401875). 2차 커밋 526edb2 "답 본문은 그대로, 미리보기(preview)만 두 문장" → **통과**(35/35). 관문 한 번 4~5초, 모델 호출 0, 워크플로에 secrets 없음. 시연 PR이라 병합하지 않고 닫았다.
- 전체 점수 −9.4%p는 48문항으로 잡을 수 있는 최소 차이 17%p(31편)보다 작다 → 전체 평균 임계값 관문(−10%p · −17%p)은 이 PR을 통과시킨다(과제 1). 그래서 문항 단위로 막는다.
- **프롬프트 · 모델을 바꾸는 PR**은 CI에서 모델을 부르지 않는다(키를 CI에 넣지 않음) → 로컬에서 다시 돌려 `runs/`를 갈아 끼운 PR로 올리고 관문이 그 출력을 채점한다. 이번 편에서는 이 경로를 실행하지 않았다(비용).
- **오프라인 vs 온라인**(운영 트래픽 없음 — 26편 53개를 운영 로그라고 침, 틀린 답 12 = 23%): 정답 없이 셀 수 있는 신호 — 빈 답 3(그중 틀림 1) · 판사 부족 배지 10(3, 틀린 답 12개 중 3개) · 반성 28(9, 12개 중 9개) · 300초 넘음 10(2) · 1센트 넘음 8(2). 어느 신호도 정답이 아니다; 반성이 걸린 기록부터 읽으면 틀린 답을 23%보다 자주(32%) 만난다. 하루 1,000건 가정 시 실패율 23%의 95% 구간: 1% 표본 ±26%p · 5% ±12%p · 10% ±8%p · 30% ±5%p.
- **대시보드**(8842): main · PR 1차 · PR 2차 세 실행을 `01_gate.py --log`로 기록(각 커밋을 git worktree로 꺼내 같은 명령) → 회귀 35/35 · 30/35 · 35/35, 문항 격자, 운영 신호 표.
- **Langfuse**(로컬 v2.95.11, docker 컨테이너 2개 · 이미지 약 1.1GB + Postgres): 데이터셋 53문항 · 실행 main · 점수 correct 올리기 1.5~6초(녹화 실행 1.5초), 다시 읽은 값 회귀 35/35 · 능력 6/18 · 평균 0.774 — 우리 숫자와 같다(점수는 우리 채점기가 매긴 값을 기록한 것). 트레이스는 공개 보기로 로그인 없이 연다. 로그인 화면에는 아무것도 입력하지 않았다.
  - Langfuse가 더해 준 것: 트레이스 · 데이터셋 · 실행 비교 화면, 운영 트레이스를 같은 곳에 모으고 점수 · 사람 검토를 붙이는 자리. 그대로인 것: 무엇을 맞다고 볼지(채점기 · 회귀 세트 · 관문 규칙)는 여전히 우리 코드다. 프레임워크 없는 판은 표준 라이브러리만으로 CI에서 몇 초.

## 면접 질문
1. "오프라인 점수는 올랐는데 운영 지표가 떨어졌다면?" → 먼저 같은 것을 재는지 본다: 오프라인 시험지가 운영 질문 분포를 닮았나(분포 표류), 운영 지표가 품질인지 대리 신호(반성 · 지연 · 불만)인지. 운영 트레이스를 표본으로 뽑아 오프라인과 같은 채점기로 채점하고, 떨어진 유형을 시험지에 더한다(Dropbox: 운영 트래픽을 오프라인과 같은 지표로 채점).
2. "회귀 세트와 능력 세트는 어떻게 나누고, CI에서 무엇을 막나요?" → 안정적으로 맞히던 문항(여러 번 돌려도 통과)은 회귀 세트로 문항 단위로 막고, 아직 못 하거나 흔들리는 문항은 능력 세트로 기록만 한다. 전체 평균으로 막으면 작은 세트에서 몇 문항 떨어진 것은 잡음 속에 묻힌다.
3. "평가 도구(Langfuse 등)를 쓰나요, 직접 만드나요?" → 채점기 · 시험지 · 관문 규칙은 직접 만들고, 트레이스 저장 · 실행 비교 화면 · 운영 표본 검토 같은 인프라는 도구를 쓴다. 옮겨 보면 숫자가 같아야 한다(우리 0.774 = Langfuse 0.774).

## 과제
1. 답 만들기를 여러 가지로 바꿔 보고, 전체 평균 임계값 관문(−5 · −10 · −17%p)과 문항 단위 관문이 각각 무엇을 막는지 센다.
2. 운영 트레이스를 10개만 읽을 수 있다면 무엇부터 읽을지: 무작위 · 반성 먼저 · 판사 부족 먼저를 비교한다.
3. PR 1차(앞 두 문장)를 Langfuse에 두 번째 실행으로 올리고 main과 문항별로 비교한다.

참고(2026-10-19 원문 확인, 사본 `sources/ops-2026-10-19/` · `agent-rag-2026-10-19/`):
- Anthropic, [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — "Capability vs. regression evals"(regression "should have a nearly 100% pass rate", 능력 평가가 "graduate"해 회귀 세트로), production monitoring "to detect distribution drift", 부록 "Langfuse provides similar capabilities as a self-hosted open-source alternative".
- Dropbox, [A practical blueprint for evaluating conversational AI at scale](https://dropbox.tech/machine-learning/practical-blueprint-evaluating-conversational-ai-at-scale-dash) — "Every pull request kicked off about 150 canonical queries … under 10 minutes", "continuously sampled live production traffic and scored it with the same metrics and logic as our offline suites", 표류 경고 · 대시보드.
