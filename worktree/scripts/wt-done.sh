#!/usr/bin/env bash
# wt-done.sh — 격리 worktree 안전 제거 (미커밋·미푸시 변경 가드)
#
# 사용:  scripts/tools/wt-done.sh <branch-name> [--force]
#   예:  scripts/tools/wt-done.sh fix/eoportal-invoices-idempotent
#
# 기본은 "잃을 변경이 없을 때만" 제거한다. 미커밋/미푸시가 있으면 멈추고 보여준다(--force 로 강제).
# node_modules·.env 는 심링크라 제거해도 메인 체크아웃 원본은 안전하다.
set -euo pipefail

ARG="${1:?사용법: wt-done.sh <branch-name|path> [--force]}"
FORCE="${2:-}"

REPO_ROOT="$(git rev-parse --show-toplevel)"
SLUG="$(printf '%s' "$ARG" | tr '/' '-')"
WT_DIR="$(dirname "$REPO_ROOT")/$(basename "$REPO_ROOT")-worktrees/$SLUG"
[ -d "$WT_DIR" ] || WT_DIR="$ARG"          # 경로 직접 전달도 허용

if [ ! -d "$WT_DIR" ]; then
  echo "❌ worktree 를 찾을 수 없음: $ARG" >&2
  echo "   현재 목록:" >&2
  git worktree list >&2
  exit 1
fi

# ── 가드 1: 미커밋 변경 (심링크 node_modules·.next·.omc·env 노이즈 제외) ────
# porcelain 은 'XY PATH' 형식 → sed 로 상태접두사 3글자 제거 후 경로만 필터.
# (심링크 node_modules 는 gitignore 'node_modules/' 디렉토리패턴에 안 걸려 ?? 로 뜸)
DIRTY="$(git -C "$WT_DIR" status --porcelain | sed 's/^...//' \
  | grep -vE '(^|/)node_modules($|/)|(^|/)\.next($|/)|(^|/)\.omc($|/)|(^|/)\.env' || true)"
# ── 가드 2: 미푸시 커밋 (upstream 대비 ahead) ─────────────────────────────
AHEAD="$(git -C "$WT_DIR" log --oneline '@{u}..' 2>/dev/null || true)"

if { [ -n "$DIRTY" ] || [ -n "$AHEAD" ]; } && [ "$FORCE" != "--force" ]; then
  echo "⚠️  잃을 수 있는 변경이 있어 멈춤: $WT_DIR"
  [ -n "$DIRTY" ] && { echo "── 미커밋 ──"; echo "$DIRTY"; }
  [ -n "$AHEAD" ] && { echo "── 미푸시 커밋 ──"; echo "$AHEAD"; }
  echo
  echo "→ 커밋/푸시 후 다시 실행하거나, 정말 버리려면: scripts/tools/wt-done.sh $ARG --force"
  exit 1
fi

echo "▶ worktree 제거: $WT_DIR"
git worktree remove --force "$WT_DIR"      # --force: 심링크 node_modules/.next 등 untracked 정리
git worktree prune
echo "✅ 제거 완료. 브랜치 ref 는 보존됨(필요 시 git branch -d $ARG)."
