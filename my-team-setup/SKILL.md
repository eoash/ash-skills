---
name: my-team-setup
description: EO Studio 팀원의 Claude Code 환경을 원클릭으로 세팅하는 온보딩 스킬. "팀 셋업", "team setup", "클로드 설치", "MCP 설정" 요청에 사용.
triggers:
  - "팀 셋업"
  - "team setup"
  - "클로드 설치"
  - "MCP 설정"
  - "온보딩"
---

# my-team-setup — EO Studio 팀원 원클릭 셋업

EO Studio 팀원이 Claude Code를 설치한 직후 실행하면, 업무에 필요한 MCP 서버 + 기본 설정 + 팀 컨텍스트를 한 번에 세팅한다.

## 실행 흐름

### Phase 0: 사전 점검

Bash로 아래 항목을 자동 체크한다. 실패 항목이 있으면 안내 후 중단.

```bash
# 1. Claude Code CLI 설치 확인
claude --version

# 2. Node.js 설치 확인 (MCP 서버 실행에 필요)
node --version

# 3. npm/npx 사용 가능 확인
npx --version
```

**실패 시 안내**:
- Claude Code 미설치 → `npm install -g @anthropic-ai/claude-code` 안내
- Node.js 미설치 → `brew install node` (Mac) 또는 https://nodejs.org 안내
- 모두 통과 → Phase 1 진행

### Phase 1: 팀원 정보 수집

AskUserQuestion으로 아래 3가지만 물어본다 (한 번에 모두):

```
EO Studio 팀 셋업을 시작합니다!

1. 이름이 뭔가요? (예: 서현)
2. 주로 어떤 업무를 하나요? (예: 재무, 편집, 사업개발, HR, 마케팅, 개발)
3. 아래 도구 중 업무에 쓰는 것을 모두 골라주세요:
   - [a] Slack (메시지, 채널 검색)
   - [b] Notion (문서, 위키)
   - [c] Google Calendar (일정 관리)
   - [d] Gmail (이메일 검색/초안)
   - [e] Airtable (데이터 관리)
   - [f] ClickUp (프로젝트 관리)
   - [g] 전부 다!
```

### Phase 2: MCP 서버 설치

팀원이 고른 도구에 맞춰 MCP를 설치한다.

#### Cloud MCP (OAuth 기반 — API 키 불필요, 브라우저 로그인만)

Anthropic 관리형 MCP는 `claude mcp add --transport cloud` 명령으로 추가한다.
팀원이 브라우저에서 OAuth 인증만 하면 되므로 가장 쉬운 방식.

| 선택 | MCP 이름 | 설치 명령 |
|------|----------|-----------|
| a | Slack | `claude mcp add Slack -t cloud -s user` |
| b | Notion | `claude mcp add Notion -t cloud -s user` |
| c | Google Calendar | `claude mcp add "Google Calendar" -t cloud -s user` |
| d | Gmail | `claude mcp add Gmail -t cloud -s user` |
| f | ClickUp | `claude mcp add ClickUp -t cloud -s user` |

#### Local MCP (API 키 필요)

| 선택 | MCP 이름 | 설치 명령 |
|------|----------|-----------|
| e | Airtable | 아래 별도 절차 |

**Airtable 설치 절차**:
1. AskUserQuestion: "Airtable Personal Access Token이 있나요? (없으면 https://airtable.com/create/tokens 에서 생성)"
2. 토큰을 받으면:
```bash
claude mcp add airtable -s user -- npx -y airtable-mcp-server --token RECEIVED_TOKEN
```

#### 각 Cloud MCP 설치 후

`claude mcp add` 실행 시 브라우저가 열리며 OAuth 인증 화면이 뜬다.
팀원에게 안내: "브라우저에서 로그인하고 '허용'을 누르면 자동으로 연결됩니다."

### Phase 3: 플러그인 활성화

EO 팀원에게 유용한 기본 플러그인을 설치한다:

```bash
# 커밋 명령어 (git commit/push/PR)
claude plugin add commit-commands@claude-plugins-official

# 코드 리뷰 (PR 리뷰)
claude plugin add code-review@claude-plugins-official
```

비개발자에게는 플러그인 설치를 생략하고, 개발자에게만 추가 제안:
```bash
# 개발자 추가 플러그인
claude plugin add pr-review-toolkit@claude-plugins-official
claude plugin add superpowers@claude-plugins-official
```

### Phase 4: 팀 CLAUDE.md 생성

팀원의 작업 디렉토리에 기본 CLAUDE.md를 생성한다.
**주의**: 이미 CLAUDE.md가 있으면 절대 덮어쓰지 않는다.

팀원의 홈 디렉토리에 `~/.claude/CLAUDE.md`가 없는 경우에만 생성:

```markdown
# CLAUDE.md — EO Studio ({이름})

## 역할
{팀원이 답한 업무 영역} 담당

## 규칙
- 한국어로 대화, 코드와 파일명은 영어
- 결과물을 설명보다 먼저 제시
- 모호하면 추측하지 말고 물어볼 것

## 자주 쓰는 도구
{선택한 MCP 목록}
```

### Phase 5: 검증 + 완료

#### 자동 검증
```bash
# 설치된 MCP 목록 확인
claude mcp list
```

출력에서 Phase 2에서 설치한 MCP들이 모두 보이는지 확인한다.

#### 완료 메시지

```
셋업 완료! {이름}님의 Claude Code 환경이 준비됐습니다.

설치된 MCP:
  {설치된 MCP 목록}

바로 해볼 수 있는 것들:
  - "오늘 캘린더 일정 알려줘"
  - "Slack #general 채널 최근 메시지 요약해줘"  
  - "Notion에서 OO 문서 찾아줘"

더 알아보기:
  - /day1-onboarding → Claude Code 기본기 학습
  - /my-context-sync → 모든 도구의 컨텍스트를 한 번에 수집
```

## 에러 핸들링

| 상황 | 대응 |
|------|------|
| `claude` 명령 없음 | npm 글로벌 설치 안내 + PATH 확인 |
| `node` 명령 없음 | brew install node 또는 공식 사이트 안내 |
| OAuth 브라우저 안 열림 | URL 직접 복사 → 브라우저 붙여넣기 안내 |
| MCP 이미 설치됨 | "이미 연결되어 있습니다" 스킵 |
| Airtable 토큰 없음 | 토큰 생성 URL 안내, 나중에 추가 가능하다고 안내 |

## 주의사항

- 이 스킬은 **팀원의 머신에서 실행**해야 한다 (서현님 머신 X)
- Cloud MCP는 scope를 `user`로 설정해서 모든 프로젝트에서 사용 가능하게 한다
- 민감한 API 키는 절대 로그에 출력하지 않는다
- CLAUDE.md가 이미 있으면 덮어쓰지 않는다
