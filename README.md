# Ash Skills

안서현(Seohyun Ahn)의 Claude Code 스킬 모음입니다.
22개 스킬 — 콘텐츠 소화, 세션 관리, 개발 자동화, 어드바이저, 교육 커리큘럼까지.

---

## 스킬 설치

### 원하는 스킬만 선택 설치 (권장)

```bash
npx skills add eoash/ash-skills -g -a claude-code
```

실행하면 인터랙티브 메뉴가 뜨고, 원하는 스킬만 선택해서 설치할 수 있어요.

### 특정 스킬만 설치

```bash
# 예: my-fetch-youtube만 설치
npx skills add eoash/ash-skills --skill my-fetch-youtube -g -a claude-code

# 예: 여러 개 동시 설치
npx skills add eoash/ash-skills --skill my-fetch-youtube --skill plan-first -g -a claude-code
```

### 전체 설치

```bash
npx skills add eoash/ash-skills --all -g -a claude-code
```

---

## 스킬 목록

### 콘텐츠 처리

| 스킬 | 설명 | 사용법 |
|------|------|--------|
| `my-fetch-youtube` | YouTube URL → 자막 추출 → 요약·인사이트·전체 번역 | `/my-fetch-youtube [URL]` |
| `my-fetch-tweet` | X/Twitter URL → 트윗 원문 → 요약·인사이트·전체 번역 | `/my-fetch-tweet [URL]` |
| `my-content-digest` | 콘텐츠를 Quiz-First 방식으로 학습 (퀴즈 → 피드백 → 공부) | `/my-content-digest` |
| `hwpx` | 한글(HWPX) 문서 생성·읽기·편집 | `/hwpx` |

### 세션 & 워크플로우 관리

| 스킬 | 설명 | 사용법 |
|------|------|--------|
| `my-session-wrap` | 세션 종료 시 작업 정리, 문서 업데이트, 학습 기록 | `/my-session-wrap` |
| `my-history-insight` | 과거 세션 기록 분석 → 패턴·인사이트 추출 | `/my-history-insight` |
| `my-session-analyzer` | 스킬 실행 기록을 SKILL.md와 비교 → PASS/FAIL 검증 | `/my-session-analyzer` |
| `my-context-sync` | Slack·Notion·Gmail·Calendar·ClickUp·GitHub 컨텍스트 통합 | `/my-context-sync` |

### 개발 & 계획

| 스킬 | 설명 | 사용법 |
|------|------|--------|
| `plan-first` | 작업 전 계획서·맥락노트·체크리스트 3문서 수립 | `/plan-first [작업내용]` |
| `opusplan` | Opus가 설계 + Sonnet이 실행하는 2단계 개발 | `/opusplan` |
| `ralph-loop` | 동일 작업을 반복 실행하며 점진적 개선하는 자율 루프 | `/ralph-loop` |
| `my-dev-team` | 4-에이전트 팀 (PM→아키텍트→개발자→리뷰어) 자동 개발 파이프라인 | `/my-dev-team` |

### 어드바이저 (커스터마이징 필요)

> 아래 스킬들은 EO Studio 맞춤 페르소나 기반입니다.
> 그대로 쓸 수도 있지만, SKILL.md 안의 페르소나·참조 경로를 본인 환경에 맞게 수정하면 더 잘 작동합니다.
> **구조를 참고해서 나만의 어드바이저를 만들어보세요.**

| 스킬 | 설명 | 사용법 |
|------|------|--------|
| `my-consult` | 키워드 감지 → Alex(코드)/Lisa(법률)/Chris(재무) 자동 라우팅 | `/my-consult` |
| `my-code-reviewer` | 코드 리뷰 어드바이저 (아키텍처 진단, SOLID 검토, 리팩터링) | `/my-code-reviewer` |
| `my-legal-advisor` | 법률 어드바이저 (계약 검토, 컴플라이언스, 리스크 평가) | `/my-legal-advisor` |
| `my-finance-advisor` | 재무 어드바이저 (AR 전략, 캐시플로우, FX 판단) | `/my-finance-advisor` |

### AI Native Camp 교육

| 스킬 | 설명 | 사용법 |
|------|------|--------|
| `day1-onboarding` | Day 1 — Claude Code 온보딩 | `/day1-onboarding` |
| `day2-create-context-sync-skill` | Day 2 — Context Sync 스킬 직접 만들기 | `/day2-create-context-sync-skill` |
| `day2-supplement-mcp` | Day 2 보충 — MCP 딥다이브 | `/day2-supplement-mcp` |
| `day4-wrap-and-analyze` | Day 4 — Session Wrap & Analyze 직접 만들기 | `/day4-wrap-and-analyze` |
| `day5-fetch-and-digest` | Day 5 — fetch-tweet, fetch-youtube, content-digest 3개 스킬 만들기 | `/day5-fetch-and-digest` |
| `my-homework-new` | 숙제 파일 자동 생성 | `/my-homework-new` |

---

## 추천 플러그인 설치

스킬 외에 함께 쓰면 좋은 플러그인 목록이에요.
`setup.sh`를 실행하면 원하는 것만 골라서 설치할 수 있어요.

```bash
bash <(curl -s https://raw.githubusercontent.com/eoash/ash-skills/main/setup.sh)
```

### 플러그인 목록

| 플러그인 | 설명 |
|----------|------|
| `superpowers` | 브레인스토밍·디버깅·코드리뷰 등 핵심 워크플로우 모음 |
| `ralph-loop` | 자율 반복 개발 루프 |
| `clarify` | 요구사항 명확화 (vague·unknown·metamedium) |
| `git-onboarding` | Git 초보자 단계별 온보딩 |
| `frontend-design` | 프로덕션 수준 프론트엔드 UI 생성 |
| `commit-commands` | commit·push·PR 자동화 |

---

## 설치 후 확인

```bash
# 설치된 스킬 목록 확인
npx skills list

# Claude Code 재시작 후 스킬 사용
/my-fetch-youtube https://youtube.com/...
```
