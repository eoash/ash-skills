#!/bin/bash
# ash-skills/config → ~/.claude 동기화 스크립트 (Mac/Linux)
# 사용법: bash sync.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

echo "=== Claude Code Config Sync ==="
echo "Source: $SCRIPT_DIR"
echo "Target: $CLAUDE_DIR"
echo ""

# 1. settings.json
cp "$SCRIPT_DIR/settings.json" "$CLAUDE_DIR/settings.json"
echo "[OK] settings.json"

# 2. hooks
mkdir -p "$CLAUDE_DIR/hooks"
cp "$SCRIPT_DIR/hooks/"* "$CLAUDE_DIR/hooks/"
echo "[OK] hooks ($(ls "$SCRIPT_DIR/hooks/" | wc -l | tr -d ' ')개 파일)"

# 3. memory — 프로젝트별 메모리 디렉토리 찾기
# eoash 프로젝트 메모리 경로 (Mac vs Windows 경로 차이 처리)
MEMORY_DIR=""
for d in "$CLAUDE_DIR/projects/"*eoash*/memory; do
  if [ -d "$d" ] || [ -d "$(dirname "$d")" ]; then
    MEMORY_DIR="$(dirname "$d")/memory"
    break
  fi
done

# eoash 프로젝트 디렉토리가 있지만 memory 폴더가 없는 경우
if [ -z "$MEMORY_DIR" ]; then
  for d in "$CLAUDE_DIR/projects/"*eoash*; do
    if [ -d "$d" ]; then
      MEMORY_DIR="$d/memory"
      break
    fi
  done
fi

if [ -n "$MEMORY_DIR" ]; then
  mkdir -p "$MEMORY_DIR"
  cp "$SCRIPT_DIR/memory/"* "$MEMORY_DIR/"
  echo "[OK] memory → $MEMORY_DIR ($(ls "$SCRIPT_DIR/memory/" | wc -l | tr -d ' ')개 파일)"
else
  echo "[SKIP] eoash 프로젝트 메모리 디렉토리를 찾을 수 없음"
  echo "       Claude Code에서 eoash 프로젝트를 한 번 열어야 디렉토리가 생성됩니다."
fi

echo ""
echo "=== 동기화 완료 ==="
