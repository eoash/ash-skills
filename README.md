# Ash Skills

안서현(Seohyun Ahn)의 Claude Code 스킬 모음입니다.

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

| 스킬 | 설명 | 사용법 |
|------|------|--------|
| `my-fetch-youtube` | YouTube URL → 자막 추출·번역·요약 | `/my-fetch-youtube [URL]` |
| `my-fetch-tweet` | X/Twitter URL → 트윗 번역·요약 | `/my-fetch-tweet [URL]` |
| `my-content-digest` | 콘텐츠 Quiz-First 학습 | `/my-content-digest` |
| `my-context-sync` | Slack·Notion·Gmail·ClickUp 컨텍스트 싱크 | `/my-context-sync` |
| `plan-first` | 작업 전 3문서(계획서·맥락노트·체크리스트) 수립 | `/plan-first [작업내용]` |
| `opusplan` | Opus 설계 + Sonnet 실행 | `/opusplan` |
| `ralph-loop` | 반복 자율 개발 루프 | `/ralph-loop` |
| `day1-onboarding` | AI Native Camp Day 1 온보딩 | `/day1-onboarding` |
| `day2-create-context-sync-skill` | AI Native Camp Day 2 Context Sync 스킬 만들기 | `/day2-create-context-sync-skill` |
| `day2-supplement-mcp` | AI Native Camp Day 2 MCP 딥다이브 | `/day2-supplement-mcp` |
| `day4-wrap-and-analyze` | AI Native Camp Day 4 세션 분석 | `/day4-wrap-and-analyze` |

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
