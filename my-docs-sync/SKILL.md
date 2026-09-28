---
name: my-docs-sync
description: EO Studio 작업 원천 MD의 경로·상태·체크리스트를 실제 체크아웃과 대조해 동기화한다. "/docs-sync", "문서 동기화", "원천 md 업데이트", "체크리스트 업데이트" 요청에 사용.
---

# my-docs-sync

EO Studio의 운영 문서를 실제 레포·파일·외부 상태와 대조해 최소 변경으로 동기화한다.

## 정본 지도

전역 진입 규칙도 함께 확인한다: `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.grok/rules/`. 작업대 및 선택 체크아웃의 `AGENTS.md`와 도구별 `rules/`는 적용 범위에 맞게 읽는다.

1. 작업대 규칙: `/Users/ash/Documents/eoash/AGENTS.md`
2. Claude memory 인덱스: `/Users/ash/.claude/projects/-Users-ash-Documents-eoash/memory/MEMORY.md`
3. 주제 상세: 위 디렉토리의 `project_*` / `feedback_*` / `reference_*` / `workflow_*` / `incident_*`
4. 코드 운영 규칙·상태: 선택한 EO 체크아웃의 `CLAUDE.md`, `STATUS.md`, `agent/memory/ANTI_PATTERNS.md`
5. Grok 요약: `/Users/ash/.grok/memory/MEMORY.md` — Claude memory의 축약본이며 경로·공통 규칙만 동기화

추가 참조: 체크아웃 `CODEX_OPERATING_LOOP.md`, `docs/system-map.md`, 프로젝트별 `CLAUDE.md`와 런북. 위키는 `/Users/ash/Documents/eoash/eo-wiki/`이며 원천 memory의 파생 열람본이다. 원천 수정과 `site/index.html` 재빌드는 별개다.

스킬 원본 저장소: `/Users/ash/Documents/eoash/ash-skills` (`eoash/ash-skills`). 설치본: `~/.agents/skills/my-docs-sync/SKILL.md`; Claude 스킬 경로는 이 폴더를 가리키는 링크다. 수정 시 원본과 설치본을 대조하고 로컬 반영과 원격 반영 여부를 각각 보고한다.

Codex generated memory(`/Users/ash/.codex/memories/`) 자체는 직접 수정하지 말고, 사용자가 메모리 업데이트를 명시한 경우에만 지정된 ad-hoc note 경로를 사용한다.

## 실행

1. `git -C /Users/ash/Developer/eoash worktree list`와 각 후보 체크아웃의 `status --short --branch`를 확인해 작업 대상을 고른다. 공유 체크아웃의 다른 세션 변경을 보존한다.
2. 선택 체크아웃에서 최근 커밋, 문서 변경, 관련 파일과 `package.json` 스크립트를 읽는다. 추측한 배포·인원·수치를 쓰지 않는다.
3. `STATUS.md`는 완료/미완료 상태와 근거를 갱신한다. Git 반영과 프로덕션 E2E 확인을 분리한다.
4. `CLAUDE.md`는 반복 적용될 운영 규칙과 최신 업데이트 포인터만 반영한다. 상세 이력을 중복하지 않는다.
5. Claude memory `MEMORY.md`는 인덱스로 유지하고, 상세는 매칭되는 topic 파일에 쓴다. 링크 대상이 실제로 존재하는지 검증한다.
6. Grok memory에서 존재하지 않는 레포·위키·심링크 경로를 고치되, 시점 의존 상태는 `As of YYYY-MM-DD`로 표시한다.
7. 변경 후 링크, 경로, Git diff, 문서 줄 수 제약을 검증한다. 커밋은 사용자가 명시한 경우에만 하며 명시적 파일 경로만 stage한다.
8. 최신 요약만 추가하고 끝내지 않는다. 같은 사실을 담은 기존 본문·인덱스·다른 에이전트 요약을 대조한다. 역사 기록에는 기준일을 붙이고, 상충하는 현재 안내는 정정한다. 파일 링크 존재 여부는 내용의 최신성 검증을 대신하지 않는다.

## 제약

- Claude memory `MEMORY.md`는 200줄 이하 인덱스로 유지한다.
- 기존 완료 체크(`[x]`)를 근거 없이 미완료로 되돌리지 않는다.
- 외부 시스템이나 프로덕션을 열어보지 않았다면 상태를 확정하지 않는다.
- 관련 없는 사용자 변경, 자동 생성 블록, 시크릿은 건드리지 않는다.
