#!/usr/bin/env bash
# wt-ls.sh — worktree 현황 한눈에 보기 (dirty/미푸시/좀비 표시)
#
# 사용:  scripts/tools/wt-ls.sh           # 전체
#        scripts/tools/wt-ls.sh --mine    # wt-new.sh 로 만든 것(eoash-worktrees/)만
#        scripts/tools/wt-ls.sh --prune   # 사라진(prunable) 좀비 항목 정리
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
MINE_BASE="$(dirname "$REPO_ROOT")/$(basename "$REPO_ROOT")-worktrees"
MODE="${1:-all}"

if [ "$MODE" = "--prune" ]; then
  echo "▶ 사라진 worktree 항목 정리(git worktree prune) — 디스크의 실제 작업물은 건드리지 않음"
  git worktree prune -v
  echo "✅ 완료"
  exit 0
fi

printf '%-58s %-12s %s\n' "PATH" "STATE" "BRANCH/HEAD"
printf '%-58s %-12s %s\n' "----" "-----" "-----------"

git worktree list --porcelain | awk '
  /^worktree /   {path=substr($0,10)}
  /^branch /     {br=substr($0,8); sub("refs/heads/","",br)}
  /^detached/    {br="(detached)"}
  /^prunable/    {prune=1}
  /^$/ {print path"\t"br"\t"(prune?"PRUNABLE":""); path="";br="";prune=0}
  END {if(path!="") print path"\t"br"\t"(prune?"PRUNABLE":"")}
' | while IFS=$'\t' read -r path br prune; do
  [ -z "$path" ] && continue
  # --mine: eoash-worktrees/ 하위만
  if [ "$MODE" = "--mine" ] && [[ "$path" != "$MINE_BASE/"* ]]; then continue; fi

  state="$prune"
  if [ -z "$state" ] && [ -d "$path" ]; then
    dirty="$(git -C "$path" status --porcelain 2>/dev/null | sed 's/^...//' \
      | grep -vE '(^|/)node_modules($|/)|(^|/)\.next($|/)|(^|/)\.omc($|/)|(^|/)\.env' || true)"
    ahead="$(git -C "$path" log --oneline '@{u}..' 2>/dev/null | wc -l | tr -d ' ' || true)"
    if [ -n "$dirty" ]; then state="DIRTY"; fi
    if [ "${ahead:-0}" != "0" ]; then state="${state:+$state,}↑$ahead"; fi
    if [ -z "$state" ]; then state="clean"; fi
  fi
  printf '%-58s %-12s %s\n' "$path" "$state" "$br"
done

echo
echo "범례: DIRTY=미커밋  ↑N=미푸시 N커밋  PRUNABLE=디렉토리 사라짐(--prune 로 정리)  clean=정리 가능"
