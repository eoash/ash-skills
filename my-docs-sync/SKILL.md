---
name: my-docs-sync
description: CLAUDE.md/MEMORY.md 당면 과제 체크박스 + 설치 현황 + 타임스탬프 자동 업데이트. "/docs-sync", "문서 동기화", "체크리스트 업데이트" 요청에 사용.
---

# my-docs-sync

프로젝트 문서(CLAUDE.md, MEMORY.md)의 당면 과제 체크박스, 설치 현황, 타임스탬프를 자동으로 업데이트하는 스킬.

## 실행 흐름

### Step 1: 현재 상태 파악

1. `git log --oneline -10`으로 최근 커밋 메시지 확인
2. `git diff --stat HEAD~5`으로 최근 변경 파일 파악
3. 프로젝트별 현황 데이터 수집:
   - token-dashboard: `ls src/lib/backfill/*.json | wc -l` → 설치 인원 수
   - 기타 프로젝트: 관련 상태 확인

### Step 2: CLAUDE.md 당면 과제 업데이트

1. `/Users/ash/Documents/eoash/CLAUDE.md`의 `## 4. 현재 진행 상태` > `### 당면 과제` 섹션을 읽는다
2. Step 1에서 파악한 최근 커밋/변경사항과 체크박스 항목을 대조
3. 완료된 항목: `[ ]` → `[x]`
4. 새로 식별된 과제: `[ ]`로 추가
5. `마지막 업데이트` 날짜를 오늘 날짜로 갱신

### Step 3: MEMORY.md 업데이트

1. `/Users/ash/.claude/projects/-Users-ash-Documents-eoash/memory/MEMORY.md` 읽기
2. 프로젝트별 설치 현황 숫자 갱신 (예: `8/27명` → 실제 backfill 파일 수 기준)
3. 완료 항목 추가/갱신
4. 날짜 업데이트

### Step 4: 프로젝트별 CLAUDE.md 업데이트 (해당 시)

변경된 파일이 속한 프로젝트의 CLAUDE.md가 있으면:
- `token-dashboard/CLAUDE.md` — 팀원 수, 주요 파일 목록 등
- `finance-dashboard/CLAUDE.md` — 세션 완료 기록 등
- `leave-dashboard/CLAUDE.md` — 체크리스트 등

### Step 5: 변경사항 확인 + 커밋

1. `git diff`로 변경 내용 미리보기
2. 사용자에게 변경 내용 보여주고 확인 요청
3. 확인 후 커밋: `git add <변경파일들> && git commit -m "docs: 당면 과제 + 현황 업데이트"`

## 사용 예시

```
/docs-sync
→ 최근 커밋 분석 → CLAUDE.md 체크박스 업데이트 → MEMORY.md 현황 갱신 → 커밋

/docs-sync token-dashboard
→ token-dashboard 관련 문서만 업데이트
```

## 주의사항

- MEMORY.md는 200줄 한도 — 인덱스만 유지, 상세는 topic 파일로
- 체크박스 변경 시 기존 완료 항목(`[x]`)을 `[ ]`로 되돌리지 않도록 주의
- 설치 현황은 backfill 파일 실제 개수 기준 (추측 금지)
