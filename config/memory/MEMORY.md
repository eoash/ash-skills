# Project Memory — Index

> 상세 내용은 각 토픽 파일 참조. MEMORY.md는 인덱스만 유지 (200줄 한도).

## 사용자
- **사용 동기와 철학**: `memory/user_motivation.md` — 솔선수범, 자산화 원칙, 전사 AI 도입 리더

## 피드백
- **git merge not rebase**: `memory/feedback_git_merge.md` — pull 시 rebase 금지, merge 사용
- **PR 자동 머지**: `memory/feedback_auto_merge.md` — PR 생성 후 gh pr merge로 바로 머지, GitHub 웹 불필요

## 프로젝트별 CLAUDE.md 구조
```
eoash/CLAUDE.md                    ← 공통 규칙 + 공통 오답노트
token-dashboard/CLAUDE.md          ← 파이프라인, OTel, Prometheus 전용
finance-dashboard/CLAUDE.md        ← Sheets, 위드택스, SA 인증 전용
leave-dashboard/CLAUDE.md          ← Airtable, 미완료 체크리스트
```

## token-dashboard
- **배포**: https://token-dashboard-iota.vercel.app
- **Vercel**: 모노레포 `eoash/eoash` 직접 연결, Root Directory: `token-dashboard/`
- **수동 배포**: `cd /Users/ash/Documents/eoash && npx vercel link --project token-dashboard --yes && npx vercel --prod --yes`
- **아키텍처 + 패턴 + 게이미피케이션**: `memory/token-dashboard.md`

## finance-dashboard
- **배포**: https://finance-dashboard-opal-xi.vercel.app
- **Vercel**: 모노레포 `eoash/eoash` 직접 연결, Root Directory: `finance-dashboard/`
- **기술 상세 (위드택스, VN 계좌, Cash Position)**: `memory/finance-dashboard.md`

## leave-dashboard
- **위치**: `leave-dashboard/` (Next.js 16 + Tailwind 4 + Airtable API)
- **데이터**: Airtable `이오테이블` (apphaMgCZMSN3ysHk)
- **미완료**: 입사일 필드, 재직자 필터, 반차 처리, Vercel 배포, Slack `/연차`

## Google Cloud
- **프로젝트**: `ash-email-487014`
- Sheets API 활성화됨

## Global Heads Weekly
- **Notion DB**: collection://2c274768-ec37-81b9-a773-000b8a63f034
- **3월 페이지**: `fb574768ec3783e8b02001904571b490`
- **Seohyun 섹션**: Cash Position → Revenue Update → A/R Status → Flip Status
- **데이터 소스**: Sheets SA key(`finance-dashboard/sa-key.json`) → Cash/Revenue/AR / Gmail → Flip
- **Flip 주주 (15명)**: `memory/flip-shareholders.md`

## claude-code-video
- **레포**: `eoash/claude-code-video` (로컬: `claude-code-video/`)
- **기술**: Remotion 4.x + React 18 + Google Cloud TTS (`ko-KR-Neural2-A`, quota header: `ash-email-487014`)
- **오답노트**: AbsoluteFill 기본 flex-direction=column, CSS animation 금지

## Anthropic 플랜 제약
- **개인별 시트 구독제**: `memory/project_anthropic_plan.md` — Admin API 조직 사용량 조회 불가, hook 기반 유지 필수

## eo-video-pipeline
- **상태**: 폐기 (3/15). 레포 보존: `eoash/eo-video-pipeline`

## 학습 노트
- **모노레포 vs 폴리레포**: `memory/concepts-monorepo.md`
- **Warp 터미널 핵심 단축키**: Cmd+D 화면 좌우 분할, Cmd+I Warp AI 호출. Dracula 테마 권장.
- **스킬 디렉토리 중복 주의**: `.claude/skills/`, `.agents/skills/`, `.agent/skills/` 등 유사 경로 혼재는 스킬 설치 도구 버전업 부산물. 실제 활성 경로는 `.claude/skills/`만 사용.
- **중첩 레포 감지법**: `claude-code-video/` 같이 하위 폴더가 별도 `.git`을 가지면 모노레포 git이 내용을 추적 못 함 (submodule 처리 필요 또는 하위 `.git` 제거 후 모노레포에 흡수).
- **Claude Code 알림**: `settings.json`에 notifications 필드 없음. Stop 훅(`~/.claude/hooks/PostToolUse`)에 `osascript -e 'display notification ...'` 추가로 구현.
- **node_modules/venv 정리**: 재생성 가능한 의존성 폴더는 정기 삭제 권장 (실사례: 3.5GB → 254MB). `npm install` / `python -m venv`로 언제든 복원 가능.

## 워크플로우 규칙
- **코드 변경은 브랜치 → PR**: 기능/버그 수정은 브랜치+PR, 문서만 수정은 main 직접 push 허용

## 공통 디자인 패턴
- 다크 테마: `#0A0A0A`, 액센트 `#00E87A` (EO 브랜드 에메랄드)
- 공통 컴포넌트: KpiCard, InfoTip(`components/InfoTip.tsx`), Sidebar (햄버거 드로어)
- 모바일: `grid-cols-2` KPI, `group/tip` 터치 tooltip
- 한/영 전환: i18n.ts + LanguageContext + useT() 훅
- 기술 스택: Next.js 16 + Tailwind 4 + recharts 3 + TypeScript 5
