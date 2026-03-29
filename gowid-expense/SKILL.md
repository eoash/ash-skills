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

Gowid 법인카드 미제출 경비를 조회하고, 용도를 지정하여 제출하는 Claude Code 스킬.

## 셋업 확인

스킬 실행 시 **반드시 먼저** 아래를 확인:

```bash
# 1. API 키 확인 (없으면 에러 메시지 출력됨)
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py whoami

# 2. Windows 사용자는 python3 대신 python 사용
python ~/.claude/skills/gowid-expense/scripts/gowid.py whoami
```

API 키가 없으면 사용자에게 안내:
> `GOWID_API_KEY`를 설정해주세요.
> - Mac/Linux: `~/.zshrc`에 `export GOWID_API_KEY="키값"` 추가
> - Windows: PowerShell `$PROFILE`에 `$env:GOWID_API_KEY="키값"` 추가
> - 키값은 Slack `#dev-ops` 채널의 고정 메시지를 확인하세요.

## 사용자 식별

```bash
# git 이메일로 Gowid userId 조회
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py whoami
# Windows: python ~/.claude/skills/gowid-expense/scripts/gowid.py whoami
```

`whoami` 결과에서 `userId`를 이후 모든 요청의 사용자 식별자로 사용.

## 헬퍼 스크립트

모든 API 호출은 `scripts/gowid.py`를 통해 수행. 경로:

```
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
- 참석자 이름 → userId 변환은 `gowid.sh members`로 조회

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

| ID | 용도 | 비고 |
|----|------|------|
| 12556 | 점심식비 | 인당 12,000원 |
| 12555 | 야근식비 | 인당 12,000원 |
| 131887 | 금요미식회(점심식비) | 인당 15,000원 |
| 12553 | 회식비 | |
| 12552 | 기타식비 | |
| 12532 | IT서비스 이용료 | 메모에 서비스명 |
| 70602 | 멤버십 구독료 | 메모에 서비스명 |
| 12536 | 매거진 구독료 | 메모에 서비스명 |
| 12551 | 업무교통비 | 출발지/도착지 |
| 12550 | 야근교통비 | |
| 12537 | 도서구입비 | |
| 12546 | 우편비 | |
| 72341 | 통신비 | |
| 72017 | 노트북 대여(정기결제) | |
| 12533 | 소모품비(10만원이하) | |
| 85747 | 업무추진비(스탭식비,촬영음료) | 프로젝트 필요 |
| 12530 | 온라인 마케팅 | 프로젝트 필요 |

## 주의사항

- 이 스킬은 **본인 경비만** 조회/제출합니다
- API 키는 회사 공용입니다. 외부에 절대 공유하지 마세요
- 제출 후 Gowid에서 관리자 승인을 기다리면 됩니다
- 이미 제출된 건은 자동으로 건너뜁니다 (중복 제출 방지)
