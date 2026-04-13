---
name: gowid-expense
description: Gowid 법인카드 경비 관리 어시스턴트. 미제출 경비 조회, 용도 지정, 제출, 자동 분류 규칙 확인. "경비", "미제출", "고위드", "gowid" 요청에 사용.
triggers:
  - "경비"
  - "미제출"
  - "내 경비"
  - "경비 제출"
  - "고위드"
  - "gowid"
---

# Gowid 경비 어시스턴트

Gowid 법인카드 미제출 경비를 조회하고, 용도를 지정하여 제출하는 Claude Code / Codex 공용 스킬.

## 셋업 확인

스킬 실행 시 **반드시 먼저** 아래를 확인:

```bash
# Codex 설치 경로
python3 ~/.codex/skills/gowid-expense/scripts/gowid.py whoami

# Claude Code 설치 경로
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py whoami

# Windows 사용자는 python3 대신 python 사용
python ~/.codex/skills/gowid-expense/scripts/gowid.py whoami
```

API 키는 스크립트에 내장되어 있어 별도 설정 불필요.

## 사용자 식별

```bash
# git 이메일로 Gowid userId 조회
python3 ~/.codex/skills/gowid-expense/scripts/gowid.py whoami
# Claude Code: python3 ~/.claude/skills/gowid-expense/scripts/gowid.py whoami
# Windows: python ~/.codex/skills/gowid-expense/scripts/gowid.py whoami
```

`whoami` 결과에서 `userId`를 이후 모든 요청의 사용자 식별자로 사용.

## 헬퍼 스크립트

모든 API 호출은 `scripts/gowid.py`를 통해 수행. 설치 경로 예시:

```
~/.codex/skills/gowid-expense/scripts/gowid.py
~/.claude/skills/gowid-expense/scripts/gowid.py
```

## 워크플로우

### 1. 내 미제출 경비 조회

사용자가 "내 경비", "미제출", "경비 보여줘" 등 요청 시:

```bash
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py my-expenses
```

결과를 **한국어 테이블**로 표시:

```
📋 미제출 경비 (N건)

| # | 날짜 | 가맹점 | 금액 | 추천 용도 | ID |
|---|------|--------|------|----------|-----|
| 1 | 03/26 | READ - MEETING ... | 30,430원 | IT서비스 이용료 | 32625805 |
```

- 금액이 USD/SGP 등 해외인 경우 원화 환산 금액도 함께 표시
- 용도 추천은 auto_rules 기반 (헬퍼가 처리)

### 2. 경비 제출

사용자가 "이거 식비로 제출해", "32625805 IT서비스로 제출" 등 요청 시:

```bash
# 용도 지정 + 제출
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py submit <expenseId> <purposeId> [--memo "메모"] [--participants "id1,id2"]
```

**식비 제출 시**:
- 인당 한도 초과(점심 12,000원, 야근 12,000원, 금요미식회 15,000원)면 참석자 필수
- "누구랑 먹었어요?" 물어보기
- 참석자 이름 → userId 변환은 `gowid.py members`로 조회

**IT서비스 제출 시**:
- 메모에 서비스명 자동 기입 (예: "Notion 워크스페이스")

### 3. 용도 목록 조회

```bash
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py purposes
```

### 4. 팀원 목록 (참석자 선택용)

```bash
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py members
```

### 5. 경비 상세 조회

```bash
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py detail <expenseId>
```

### 6. 자동 분류 규칙 조회

```bash
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py rules [검색어]
```

### 7. 규칙 추가 제안

사용자가 "이 가맹점 규칙 추가해줘" 요청 시:
1. 가맹점 패턴, 용도, 메모를 확인
2. GitHub Issue 생성 제안:

```bash
gh issue create --repo EO-Studio-Dev/gowid-expense-bot \
  --title "규칙 추가: <가맹점> → <용도>" \
  --body "패턴: <pattern>\n용도: <purposeName> (ID: <purposeId>)\n메모: <memo>\n제안자: $(git config user.email)"
```

## 용도 ID 빠른 참조

| ID | 용도 | API 제출 | 비고 |
|----|------|---------|------|
| 12556 | 점심식비 | ✅ 가능 | 인당 12,000원 |
| 12555 | 야근식비 | ✅ 가능 | 인당 12,000원 |
| 131887 | 금요미식회(점심식비) | ✅ 가능 | 인당 15,000원 |
| 12553 | 회식비 | ✅ 가능 | |
| 12552 | 기타식비 | ✅ 가능 | |
| 12532 | IT서비스 이용료 | ✅ 가능 | 메모에 서비스명 |
| 70602 | 멤버십 구독료 | ✅ 가능 | 메모에 서비스명 |
| 12536 | 매거진 구독료 | ✅ 가능 | 메모에 서비스명 |
| 12546 | 우편비 | ✅ 가능 | |
| 72341 | 통신비 | ✅ 가능 | |
| 72017 | 노트북 대여(정기결제) | ✅ 가능 | |
| 12533 | 소모품비(10만원이하) | ✅ 가능 | |
| 12551 | 업무교통비 | ✅ 가능 | 필수항목: 출발지/도착지 (`--requirements`) |
| 12550 | 야근교통비 | ✅ 가능 | 필수항목: 출퇴근 시간 (`--requirements`) |
| 12537 | 도서구입비 | ✅ 가능 | 필수항목: 책 제목 (`--requirements`) |
| 12531 | 서류발급비 | ✅ 가능 | 필수항목: 프로젝트명 (`--requirements`) |
| 85747 | 업무추진비(스탭식비,촬영음료) | ✅ 가능 | 프로젝트 필요 |
| 12530 | 온라인 마케팅 | ✅ 가능 | 프로젝트 필요 |

## 필수항목(Requirements) 있는 용도 제출

일부 용도는 필수 입력항목이 있다 (예: 업무교통비 → 출발지/도착지, 도서구입비 → 책 제목).
모든 필수항목은 현재 TEXT 타입이며, `purposeRequirementAnswerMap`으로 API 제출 가능.

**제출 워크플로우:**
1. `purposes` 커맨드에서 `hasRequirements: true`인 용도의 `requirements` 배열 확인
2. 필수항목이 SELECT/SELECT_MULTI 타입이면 `purpose-requirements <purposeId>`로 선택지 조회
3. 사용자에게 필수항목 값 확인 후, `--requirements` 플래그로 제출

```
# 필수항목 상세 조회
python3 gowid.py purpose-requirements 12551

# 필수항목 포함 제출
python3 gowid.py submit <expenseId> 12551 --requirements '{"126": ["서울역에서 강남역"]}' --memo "출장"
```

**자동 분류 규칙 활용:**
- `rules` 커맨드의 `requirement_answer`(memo 필드) 값이 있으면 TEXT 타입 필수항목의 답으로 활용 가능
- IT서비스(12532), 멤버십(70602), 매거진(12536)은 `isRequired: false`라 필수항목 없이 제출 가능

**필수항목 미입력 시**: 400 Bad Request 에러 반환 (이전에는 500이었으나 2026-04 수정됨)

**이미 제출된 건(SUBMITTED)은 API로 변경/취소 불가**:
- 제출 취소 엔드포인트 없음 (DELETE, cancel 모두 404)
- SUBMITTED 상태에서 용도 변경 PUT → 500 에러
- 잘못 제출된 건은 반드시 Gowid 웹에서 수정해야 함
- Gowid 확인 (2026-04): 제출 후 수정/취소 API는 현재 미지원이며, 향후 개선 검토 중

## 주의사항

- 이 스킬은 **본인 경비만** 조회/제출합니다
- API 키는 회사 공용입니다. 외부에 절대 공유하지 마세요
- 제출 후 Gowid에서 관리자 승인을 기다리면 됩니다
- 이미 제출된 건은 자동으로 건너뜁니다 (중복 제출 방지)
- **필수항목 강제 용도는 API 제출 불가** — Gowid 웹에서 직접 제출 안내
