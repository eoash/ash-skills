---
name: worktree
description: 병렬 에이전트 세션을 git worktree로 격리해 충돌(서로의 uncommitted 변경·빌드캐시 덮어쓰기)을 막는 스킬. worktree 생성/현황/안전제거. "worktree", "워크트리", "세션 격리", "병렬 세션", "wt-new" 요청에 사용.
triggers:
  - "worktree"
  - "워크트리"
  - "세션 격리"
  - "병렬 세션"
  - "wt-new"
  - "wt-ls"
  - "wt-done"
---

# git worktree 격리 스킬

여러 Claude/Codex 세션을 동시에 돌릴 때 **메인 체크아웃을 공유하면 서로의 uncommitted 변경·`.next` 빌드캐시를 조용히 덮어쓴다.** 세션마다 격리된 worktree를 주면 소스·빌드·상태가 물리적으로 분리되어 충돌이 원천 차단된다.

> 왜: 2026-06-10 두 Claude 세션이 메인 체크아웃에서 동시 작업 → 한쪽 edit가 다른 쪽을 덮어쓸 뻔함. worktree 격리로 재발 차단.

## 스크립트 (설치 경로)

```bash
# Claude Code
~/.claude/skills/worktree/scripts/wt-new.sh <branch> [base=main]
~/.claude/skills/worktree/scripts/wt-ls.sh [--mine|--prune]
~/.claude/skills/worktree/scripts/wt-done.sh <branch> [--force]

# Codex
~/.codex/skills/worktree/scripts/wt-new.sh <branch> [base=main]
```

레포에 커밋된 동일 도구가 `scripts/tools/wt-*.sh`에도 있다(eoash 한정). 스크립트는 `git rev-parse --show-toplevel`로 repo root를 찾으므로 **CWD가 어느 git 레포든 그 레포 기준**으로 동작한다.

## 표준 워크플로우

```bash
# 1) 세션용 worktree 생성 (origin/main 에서 새 브랜치 분기 + node_modules 심링크)
~/.claude/skills/worktree/scripts/wt-new.sh fix/foo

# 2) 그 디렉토리에서 새 세션 시작 → 메인·타 세션과 충돌 0
cd ~/Documents/<repo>-worktrees/fix-foo && claude

# 3) 작업 → 커밋 → 푸시 → PR (worktree 안에서)
git add <파일> && git commit -m "..." && git push -u origin fix/foo && gh pr create

# 4) PR 머지 후 정리
~/.claude/skills/worktree/scripts/wt-done.sh fix/foo
```

## 동작 요약

- **wt-new**: 레포 바깥 sibling `<repo>-worktrees/<slug>`에 worktree 생성, `origin/<base>`에서 분기(기존 브랜치면 체크아웃). 루트+각 워크스페이스 `node_modules`·`.env`를 메인 체크아웃에서 **심링크**(npm install/cp 불필요).
- **wt-ls**: 전체 worktree 현황 — `clean`/`DIRTY`(미커밋)/`↑N`(미푸시)/`PRUNABLE`(디렉토리 사라짐). `--mine`은 이 스킬이 만든 것만, `--prune`은 좀비 정리.
- **wt-done**: 미커밋·미푸시 가드 통과 시에만 제거(`--force`로 강제). 브랜치 ref·커밋은 보존(작업 디렉토리만 삭제).

## 🚨 가드레일 / 함정 (반드시 지킬 것)

- **worktree에서 `npm install` 금지** — node_modules가 심링크라 메인 체크아웃을 오염시킴.
- **배포는 git push 경로만, `vercel --prod` CLI 금지** — 심링크 node_modules는 CLI 업로드 시 `ENOTDIR`, `.vercelignore !.git`은 fsmonitor 소켓으로 깨짐. 원격 git-integration 빌드는 클린 체크아웃이라 무관.
- **clean한 worktree는 제거해도 커밋 손실 0** — `git worktree remove`는 작업 디렉토리만 지우고 브랜치 ref·커밋은 `.git`에 남음. 진짜 위험은 **DIRTY(미커밋)**뿐.
- **심링크 node_modules는 `git status`에 `?? node_modules`로 뜸** — gitignore `node_modules/`(디렉토리 패턴)가 심링크를 안 가림. **절대 `git add` 하지 말 것.** wt-ls/wt-done은 경로 기반 필터로 이 노이즈를 제외함.
- **npm workspaces 자기참조** — 루트 `node_modules/<ws>`는 메인 소스를 가리킴. 앱을 직접 빌드(`cd <app> && next build`)하면 CWD·`@/*`에서 잡혀 안전. 워크스페이스를 패키지명으로 import하면 메인 소스를 읽을 수 있음.

상세 함정 카탈로그·설계 결정: 레포 `docs/git-worktree-parallel.md` 참조.
