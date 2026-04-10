---
name: my-meeting-digest
description: ClickUp AI Notetaker 미팅 노트를 로컬 자산으로 변환. "미팅 정리", "meeting digest", "미팅 자산화", "노트 정리" 요청에 사용.
triggers:
  - "미팅 정리"
  - "미팅 자산화"
  - "meeting digest"
  - "노트 정리"
  - "회의 정리"
---

# My Meeting Digest

ClickUp AI Notetaker가 생성한 미팅 노트를 가져와서,
한국어 구조화 마크다운으로 변환하고 `eo-wiki/meetings/`에 자산으로 저장하는 스킬.

## 파이프라인

```
ClickUp AI Notetaker (자체 녹음+요약)
  → scripts/tools/clickup_meeting_notes.py
  → Claude가 한국어 변환 + 인사이트 추출
  → eo-wiki/meetings/YYYY-MM-DD_미팅명.md 저장
```

## 실행 흐름

### Step 1: 미팅 노트 선택

사용자가 ClickUp URL을 제공한 경우:
```bash
python3 scripts/tools/clickup_meeting_notes.py url "{URL}"
```

URL 없이 실행한 경우 — 목록에서 선택:
```bash
python3 scripts/tools/clickup_meeting_notes.py list 15
```
사용자에게 번호를 물어서 선택하게 한다.

### Step 2: 원본 저장

선택한 미팅 노트를 원본 그대로 저장:
```bash
python3 scripts/tools/clickup_meeting_notes.py save {DOC_ID}
```
저장 경로: `~/Documents/eo-wiki/meetings/YYYY-MM-DD_미팅명.md`

### Step 3: 한국어 다이제스트 생성

원본 파일을 읽고, 아래 구조의 **한국어 다이제스트**를 같은 디렉토리에 저장한다.
파일명: `YYYY-MM-DD_미팅명_digest.md`

#### 다이제스트 템플릿

```markdown
---
title: "{미팅명} — 다이제스트"
date: YYYY-MM-DD
source: clickup
doc_id: {DOC_ID}
type: meeting-digest
original: "{원본 파일명}.md"
---

# {미팅명}

**일시**: YYYY-MM-DD HH:MM
**참석자**: 이름1, 이름2, ...

## 핵심 요약 (3-5문장)

미팅의 핵심 내용을 한국어로 요약한다.

## 주요 결정사항

- **[결정1]**: 구체적 내용
- **[결정2]**: 구체적 내용

## 액션 아이템

| 담당자 | 할 일 | 기한 |
|--------|-------|------|
| 이름 | 구체적 액션 | 날짜/미정 |

## 인사이트

### 핵심 메시지
이 미팅에서 가장 중요한 한 가지.

### 시사점
EO Studio 운영 관점에서의 의미.

### 서현 액션
서현(나)이 후속으로 해야 할 구체적 행동.

## 원본 요약 (영→한 번역)

ClickUp AI Notetaker가 생성한 Overview, Key Takeaways, Next Steps를 한국어로 번역.
Topic별 상세 내용도 핵심만 한국어로 정리.
```

### Step 4: memory 컨텍스트 반영

다이제스트의 **주요 결정사항**을 기존 memory 파일과 대조한다.

#### 규칙
- **새 파일 생성 금지** (사용자 컨펌 없이)
- **기존 memory 파일 업데이트만** 자동 수행
- 새 프로젝트/주제가 등장한 경우 → "memory 파일 만들까요?" 컨펌

#### 프로세스
1. 다이제스트의 결정사항/상태변화 항목 추출
2. `~/.claude/projects/-Users-ash-Documents-eoash/memory/` 내 기존 파일과 매칭
3. 매칭되는 파일이 있으면 → 상태 업데이트 제안 (한 줄 추가 또는 체크박스 변경)
4. 매칭 안 되는 새 주제 → 사용자에게 "memory 만들까요?" 확인
5. 일시적 논의 (결정 아닌 것) → memory에 반영하지 않음 (eo-wiki 다이제스트에만 보존)

#### 판단 기준: memory 반영 O vs X

| 반영 O (상태 변화) | 반영 X (일시적 논의) |
|---|---|
| "에이전트 단일화 결정" | "채용 얘기가 나왔다" |
| "4월 자동화 목표 설정" | "콘텐츠 성과 비교 논의" |
| "사무실 이전 검토 시작" | "예산 고민 공유" |
| "인보이스 보류 결정" | "다음에 더 얘기하자" |

핵심: **"~하기로 했다"** = memory, **"~에 대해 얘기했다"** = 다이제스트만

### Step 5: 완료 보고

사용자에게:
1. 저장된 파일 경로 (원본 + 다이제스트)
2. 핵심 요약 3문장
3. 서현 액션 아이템 목록
4. memory 업데이트 내역 (어떤 파일에 무엇을 반영했는지)
5. "Notion에도 반영할까요?" 확인 (GHW인 경우)

### Step 6 (선택): Notion GHW 페이지 반영

GHW(Global Heads Weekly) 미팅인 경우, 다이제스트 완료 후 "Notion에도 반영할까요?" 확인.

사용자가 승인하면:
1. `scripts/lib/notion.py`의 `NotionWriter` 사용
2. GHW Notion DB에 해당 주차 페이지 찾기 (collection://2c274768-ec37-81b9-a773-000b8a63f034)
3. Seohyun 섹션에 다이제스트 핵심 요약 + 액션 아이템 추가
4. **반드시 사용자 컨펌 후** API 호출 (feedback_notion_confirm 규칙)

## 자동 알림 (폴링)

`scripts/tools/meeting_digest_poll.py`가 새 미팅 노트를 감지하면 Slack DM으로 알림.

```bash
# 수동 실행
python3 scripts/tools/meeting_digest_poll.py

# 테스트 (알림 없이)
python3 scripts/tools/meeting_digest_poll.py --dry-run
```

launchd로 15분 간격 자동 실행 설정 가능.
알림 대상: 서현 DM (SLACK_USER_ID: U04PJRXKM1Y)

## 주의사항

- 원본은 ClickUp AI Notetaker가 영어로 생성 → 다이제스트는 반드시 한국어로
- 참석자 이름은 한국어로 변환 (Taeyong Kim → 김태용 등)
- Notion 반영 시 사용자 컨펌 필수 (feedback_notion_confirm 규칙)
- Transcript(전문) 부분은 다이제스트에 포함하지 않음 (원본 파일에만 보존)

## 환경 요구사항

- `CLICKUP_API_KEY`: eo-portal/.env.local에 설정됨
- `SLACK_BOT_TOKEN`: .env에 설정됨 (Ash Bot 앱)
- 저장 경로: `~/Documents/eo-wiki/meetings/`
- ClickUp Workspace ID: `90181381526`
- Notion GHW DB: `2c274768-ec37-81b9-a773-000b8a63f034`
