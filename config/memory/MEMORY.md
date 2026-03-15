# Memory

## 사용자
- **사용 동기와 철학**: `user_motivation.md` — 솔선수범, 자산화 원칙, 전사 AI 도입 리더

## 피드백 (규칙)
- git pull 시 rebase 금지, merge 사용: `feedback_git_merge.md`
- PR 생성 후 `gh pr merge --merge --delete-branch` 즉시: `feedback_auto_merge.md`

## 프로젝트별 CLAUDE.md 구조
```
eoash/CLAUDE.md              ← 공통 규칙 + 오답노트
token-dashboard/CLAUDE.md    ← OTel, Prometheus 전용
finance-dashboard/CLAUDE.md  ← Sheets, 위드택스 전용
leave-dashboard/CLAUDE.md    ← Airtable, 미완료 체크리스트
```

## 주요 프로젝트
- **token-dashboard**: `token-dashboard.md` — Next.js + OTel/Prometheus, Vercel 배포
- **finance-dashboard**: `finance-dashboard.md` — Sheets API, 위드택스, Cash Position
- **eo-video-pipeline**: `eo-video-pipeline.md` — Gemini 2.5 Flash + FCPXML 편집 자동화
- **leave-dashboard**: Next.js 16, Airtable `이오테이블` (apphaMgCZMSN3ysHk)

## Global Heads Weekly
- Notion DB: collection://2c274768-ec37-81b9-a773-000b8a63f034
- 데이터 소스: Sheets SA key (`finance-dashboard/sa-key.json`) + Gmail (Flip)
- Flip 주주 (15명): `flip-shareholders.md`

## Google Cloud
- 프로젝트: `ash-email-487014`, Sheets API 활성화됨

## Anthropic 플랜 구조
- `project_anthropic_plan.md` — Team 플랜 vs API Org 분리, Admin API 팀 데이터 접근 불가

## claude-quest Windows 환경
- Go 1.26.0: `winget install GoLang.Go`
- GCC: `winget install BrechtSanders.WinLibs.POSIX.UCRT` (MinGW-w64 15.2.0)
- 소스: `C:\Users\ash\claude-quest-src\`, npm 바이너리: `...node_modules\claude-quest\bin\cq.exe`
- Windows 버그: `watcher.go` `encodeProjectPath`에 `\`→`-`, `:`→`-` 추가

## Instagram 카드뉴스
- 계정: `claude.ahn`, 참고: @ai_freaks.kr, 상세: `instagram_caption_style.md`
- 템플릿 수정: cover.html icon-area 580→360px, content-stat.html emphasis 160→140px + nowrap

## AI Native 교육 시리즈 (진행중)
- 상세: `ai_native_series.md`

## Chrome 자동화 패턴 (claude-in-chrome)
- Apps Script: `navigate` 불가 → `window.open(url)` 새 탭
- Monaco 한국어: `\uXXXX` 유니코드 후 `editor.setValue()`
- 비공개 Sheets: `export?format=csv&gid={시트번호}` URL 활용
- 끊김 복구: `tabs_context_mcp` 탭 ID 재확인

## 타운홀 슬라이드 / Remotion
- **PPTX**: `make_pptx_editable.py` → `townhall_finance_editable.pptx`
- 디자인: 다크 미니멀 (#0A0A0A/#E8FF47), 1280x720, Malgun Gothic
- **Remotion**: `townhall/remotion-video/`, 렌더: `remotion render src/index.ts [Id] out/output.mp4`
- 덱 ID: `1LSW7jCnaxExn3sgp84gVRQdLCjBEUzJUNAPtb1RWabM`

## python-pptx 패턴
- 4행 균등분배: `ROWY = (CH-40)//4`
- PermissionDenied = 파일 열려있음 → 닫고 재실행
- openpyxl 숫자 데이터 안정적 (한글 레이블 인코딩 주의)

## claude-code-video
- 레포: `eoash/claude-code-video` (로컬: `claude-code-video/`)
- Remotion 4.x + React 18 + Google Cloud TTS (`ko-KR-Neural2-A`, quota: `ash-email-487014`)
- 오답노트: AbsoluteFill 기본 flex-direction=column, CSS animation 금지

## 개념 참고
- 모노레포 vs 폴리레포: `concepts-monorepo.md`

# currentDate
Today's date is 2026-03-16.
