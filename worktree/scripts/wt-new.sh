#!/usr/bin/env bash
# wt-new.sh — 병렬 에이전트 세션용 "격리 git worktree" 생성 (npm workspaces 모노레포 대응)
#
# 왜: 여러 Claude/Codex 세션이 한 레포 체크아웃을 공유하면
#     서로의 uncommitted 변경·.next 빌드캐시를 조용히 덮어쓴다(2026-06-10 invoices 충돌).
#     세션마다 worktree로 격리하면 소스·빌드·상태가 물리적으로 분리되어 충돌이 원천 차단된다.
#
# 사용:  scripts/tools/wt-new.sh <branch-name> [base-branch=main]
#   예:  scripts/tools/wt-new.sh fix/eoportal-invoices-idempotent
#        scripts/tools/wt-new.sh feat/foo develop
#
# 끝나면: scripts/tools/wt-done.sh <branch-name>  로 정리
set -euo pipefail

BRANCH="${1:?사용법: wt-new.sh <branch-name> [base-branch]}"
BASE="${2:-main}"

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# worktree 는 레포 바깥 sibling 디렉토리에 둔다.
#  - 레포 안에 두면 git/빌더가 스캔하고, harness 의 .claude/worktrees 와 혼동된다.
#  - /tmp 는 재부팅 시 사라져 prunable 좀비가 됨(현재 /private/tmp 에 좀비 2개 존재).
SLUG="$(printf '%s' "$BRANCH" | tr '/' '-')"
WT_BASE="$(dirname "$REPO_ROOT")/$(basename "$REPO_ROOT")-worktrees"   # 예: eoash → eoash-worktrees
WT_DIR="$WT_BASE/$SLUG"

if [ -e "$WT_DIR" ]; then
  echo "❌ 이미 존재: $WT_DIR" >&2
  echo "   이어가기:  cd $WT_DIR" >&2
  echo "   제거:      scripts/tools/wt-done.sh $BRANCH" >&2
  exit 1
fi

echo "▶ origin 최신화..."
git fetch origin --quiet

mkdir -p "$WT_BASE"

# 브랜치가 이미 있으면(로컬/원격) 그걸 체크아웃, 없으면 origin/BASE 에서 새로 분기.
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  echo "▶ 기존 로컬 브랜치 '$BRANCH' 를 worktree 로 체크아웃"
  git worktree add "$WT_DIR" "$BRANCH"
elif git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  echo "▶ 원격 브랜치 origin/$BRANCH 를 추적하는 worktree 생성"
  git worktree add --track -b "$BRANCH" "$WT_DIR" "origin/$BRANCH"
else
  echo "▶ origin/$BASE 에서 새 브랜치 '$BRANCH' 분기"
  git worktree add -b "$BRANCH" "$WT_DIR" "origin/$BASE"
fi

# ── node_modules / env 공유 ─────────────────────────────────────────────
# 루트 node_modules 만 939M. worktree 마다 npm install(분 단위) 이나 cp(1GB+) 는 비현실적.
# 메인 체크아웃의 node_modules 를 심링크로 공유한다(기존 harness worktree 와 동일 방식).
#
# ⚠️ 심링크 node_modules = git push 전용. `vercel --prod` CLI 는 깨진다
#    (심링크 업로드 ENOTDIR / .git fsmonitor 소켓 — .claude/rules/vercel-deploy.md).
#    worktree 에서는 절대 `npm install` 하지 말 것(메인 node_modules 를 오염시킴).
# ⚠️ npm workspaces 함정: 루트 node_modules/<workspace> 는 ../<workspace>(메인 소스)를 가리킨다.
#    앱을 직접 빌드(cd worktree/<app> && next build)하면 소스는 CWD·@/* alias 에서 잡혀 안전하나,
#    워크스페이스를 "패키지명으로" import 하면 메인 소스를 읽을 수 있음(이 레포에선 해당 없음).
link_into() {            # link_into <subdir> <name>
  local sub="$1" name="$2"
  local src="$REPO_ROOT${sub:+/$sub}/$name"
  local dstdir="$WT_DIR${sub:+/$sub}"
  [ -e "$src" ] || return 0
  [ -e "$dstdir/$name" ] && return 0     # 워크스페이스가 추적했으면(드묾) 그대로 둠
  mkdir -p "$dstdir"
  ln -s "$src" "$dstdir/$name"
}

echo "▶ node_modules·env 심링크(메인 체크아웃 공유)"
WORKSPACES="$(node -e "console.log((require('$REPO_ROOT/package.json').workspaces||[]).join(' '))")"
# 루트
link_into "" node_modules
link_into "" .env
# 각 워크스페이스
for ws in $WORKSPACES; do
  link_into "$ws" node_modules
  link_into "$ws" .env
  link_into "$ws" .env.local
done
echo "  ↳ 완료 (node_modules 는 링크 — worktree 에서 npm install 금지)"

cat <<EOF

✅ 격리 worktree 준비 완료
   브랜치 : $BRANCH   (base: origin/$BASE)
   경로   : $WT_DIR

다음 단계
  cd "$WT_DIR"
  claude            # 이 디렉토리에서 새 세션 시작 → 메인·타 세션과 충돌 0
  # 작업 → git add <파일> → git commit → git push -u origin $BRANCH → gh pr create

가드레일
  • 배포는 git push 경로만 (vercel --prod CLI 금지 — 심링크 node_modules)
  • worktree 안에서 npm install 금지 (메인 node_modules 공유 중)
  • 끝나면: scripts/tools/wt-done.sh $BRANCH
EOF
