---
name: ralph-loop
description: Ralph Loop - 동일한 작업을 반복 실행하며 점진적으로 개선하는 자율 개발 루프. 매 이터레이션마다 이전 작업 결과를 보고 더 나아진다. "/ralph-loop", "ralph loop", "반복 개발", "자율 루프" 요청에 사용.
triggers:
  - "/ralph-loop"
  - "ralph loop"
  - "ralph-loop"
  - "반복 개발"
  - "자율 루프"
---

# Ralph Loop

Geoffrey Huntley의 Ralph 기법 기반 자율 반복 개발 루프.

**핵심 원리**: 동일한 작업을 반복 실행하되, 매 이터레이션마다 이전 결과(파일, 변경 내역)를 보고 점진적으로 개선한다.

---

## 호출 형식

```
/ralph-loop <작업 설명> [--max-iterations N] [--completion-promise "완료 문구"]
```

**예시:**
```
/ralph-loop "할 일 관리 REST API 구현해줘" --max-iterations 5
/ralph-loop "auth 버그 고쳐줘" --completion-promise "FIXED" --max-iterations 10
/ralph-loop "코드 리팩토링해줘" --max-iterations 3
```

**기본값:**
- `--max-iterations`: 5
- `--completion-promise`: 없음 (max-iterations까지 실행)

---

## 저장 구조

```
[프로젝트 루트]/.ralph/
  ├── PROMPT.md       ← 작업 목표 (고수준)
  ├── fix_plan.md     ← 구체적 작업 목록 (체크리스트)
  ├── AGENT.md        ← 빌드/테스트 명령어
  └── logs/
      └── iteration-N.md   ← 이터레이션별 진행 기록
```

---

## 실행 흐름

### Phase 0: 인수 파싱

스킬이 호출되면 사용자 입력에서 다음을 추출한다:

1. **작업 설명** (`<작업 설명>`): 수행할 작업의 핵심 목표
2. **max-iterations** (`--max-iterations N`): 최대 반복 횟수. 없으면 기본값 5
3. **completion-promise** (`--completion-promise "문구"`): 완료 신호 문구. 없으면 max-iterations까지만 실행

인수가 모호하면 AskUserQuestion으로 확인한다.

---

### Phase 1: 셋업

`.ralph/` 디렉토리를 생성하고 아래 파일들을 만든다.

#### `.ralph/PROMPT.md` 생성

```markdown
# Ralph Loop - 작업 목표

## 작업 설명
[사용자가 입력한 작업 설명 그대로]

## 완료 조건
[--completion-promise가 있으면: "아래 문구를 출력하면 완료: <promise>문구</promise>"]
[없으면: "max-iterations 도달 시 완료"]

## 규칙
- 매 이터레이션 시작 시 .ralph/fix_plan.md를 읽고 미완료 항목을 확인한다
- 작업 후 .ralph/fix_plan.md에서 완료된 항목을 체크한다
- 이터레이션 결과를 .ralph/logs/iteration-N.md에 기록한다
- 완료 신호는 <promise>문구</promise> 형식으로 출력한다
```

#### `.ralph/fix_plan.md` 생성

작업 설명을 분석해서 구체적인 하위 작업으로 분해한다:

```markdown
# Fix Plan

## 상태: 진행중
## 마지막 업데이트: [현재 날짜]

## 작업 목록

- [ ] [하위 작업 1]
- [ ] [하위 작업 2]
- [ ] [하위 작업 3]
...

## 완료 기록
(완료된 항목이 여기로 이동)
```

#### `.ralph/AGENT.md` 생성

```markdown
# Agent Instructions

이 프로젝트에서 사용할 주요 명령어:
- 빌드: [감지된 빌드 명령, 없으면 "N/A"]
- 테스트: [감지된 테스트 명령, 없으면 "N/A"]
- 실행: [감지된 실행 명령, 없으면 "N/A"]
```

`.ralph/logs/` 디렉토리도 생성한다.

셋업 완료 후 사용자에게 보고:
```
🔄 Ralph Loop 시작!

작업: [작업 설명]
최대 이터레이션: N회
완료 조건: [문구 or "N회 완료 후"]

.ralph/ 구조 생성 완료.
이터레이션 1 시작...
```

---

### Phase 2: 이터레이션 루프

`current_iteration = 1`부터 시작하여 아래를 반복한다.

#### 각 이터레이션 실행

Task 에이전트로 이터레이션을 실행한다:

```
Task(
  description="Ralph Loop 이터레이션 N",
  prompt="""
당신은 Ralph Loop의 이터레이션 N을 실행하는 에이전트입니다.

## 작업 목표
[PROMPT.md 내용]

## 현재 상태
[fix_plan.md 내용]

## 이전 이터레이션 요약
[iteration-(N-1).md 내용, 없으면 "첫 번째 이터레이션"]

## 지시사항

1. fix_plan.md에서 미완료 항목을 확인한다
2. 가장 중요한 미완료 항목부터 작업한다
3. 실제로 파일을 수정/생성하며 작업한다
4. 작업 완료 후 fix_plan.md에서 해당 항목을 [x]로 표시한다
5. .ralph/logs/iteration-N.md에 이터레이션 기록을 남긴다:
   - 이번에 한 작업
   - 완료된 항목
   - 남은 항목
   - 전체 진행률 (%)
   - [completion-promise가 있을 경우] 완료 조건 달성 여부

[completion-promise가 있을 경우]
완료 조건("문구")이 달성되면 반드시 다음 형식으로 출력하라:
<promise>문구</promise>

모든 작업이 완료되었다면 iteration 기록 마지막에 EXIT_SIGNAL: true를 추가하라.
"""
)
```

#### 완료 조건 확인

에이전트 출력과 `iteration-N.md`를 확인한다:

1. **completion-promise가 있는 경우**: 에이전트 출력에 `<promise>문구</promise>`가 있으면 → 루프 종료
2. **fix_plan.md 전체 완료**: 모든 항목이 `[x]`면 → 루프 종료
3. **EXIT_SIGNAL: true**: iteration 기록에 있으면 → 루프 종료
4. **max-iterations 도달**: current_iteration >= max_iterations → 루프 종료

위 조건 중 하나도 해당 없으면 `current_iteration += 1` 후 다음 이터레이션 실행.

---

### Phase 3: 완료 보고

루프 종료 후 최종 보고서를 출력한다:

```
✅ Ralph Loop 완료!

작업: [작업 설명]
총 이터레이션: N회
종료 이유: [완료 조건 달성 / 전체 태스크 완료 / max-iterations 도달]

## 진행 요약
[각 이터레이션별 한 줄 요약]

## 최종 fix_plan.md 상태
[완료된 항목들]
[미완료 항목들 (있다면)]

## 생성/수정된 파일
[변경된 파일 목록]

다음 단계: [미완료 항목이 있다면 제안, 없다면 "모든 작업 완료"]
```

---

## 중단 방법

루프 중 사용자가 중단하면:
1. 현재 이터레이션 완료 후 종료
2. fix_plan.md에 현재 상태 저장
3. 중단 보고 출력

`/cancel-ralph` 또는 `/ralph-cancel` 호출 시에도 동일하게 처리.

---

## 주의사항

- 각 이터레이션은 독립적인 Task 에이전트로 실행된다 (이전 이터레이션 파일을 통해 컨텍스트 공유)
- `.ralph/` 디렉토리가 이미 존재하면 기존 fix_plan.md를 이어받아 계속 진행
- 작업 성격에 따라 max-iterations 추천값: 단순 구현 3-5회, 복잡한 리팩토링 5-10회, 버그 수정 3-7회
