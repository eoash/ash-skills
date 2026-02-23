#!/bin/bash
# EO Studio - Claude Code 추천 플러그인 설치 스크립트

SETTINGS_FILE="$HOME/.claude/settings.json"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Claude Code 추천 플러그인 설치 가이드    ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# settings.json 존재 확인
if [ ! -f "$SETTINGS_FILE" ]; then
  echo "❌ ~/.claude/settings.json 파일이 없습니다."
  echo "   Claude Code를 먼저 실행한 뒤 다시 시도해주세요."
  exit 1
fi

# 플러그인 목록 정의
declare -a PLUGIN_KEYS=(
  "superpowers@claude-plugins-official"
  "ralph-loop@claude-plugins-official"
  "clarify@team-attention-plugins"
  "git-onboarding@git-for-everyone"
  "frontend-design@claude-plugins-official"
  "commit-commands@claude-plugins-official"
)

declare -a PLUGIN_NAMES=(
  "superpowers       — 브레인스토밍·디버깅·코드리뷰 핵심 워크플로우"
  "ralph-loop        — 자율 반복 개발 루프"
  "clarify           — 요구사항 명확화 (vague·unknown·metamedium)"
  "git-onboarding    — Git 초보자 단계별 온보딩"
  "frontend-design   — 프로덕션 수준 프론트엔드 UI 생성"
  "commit-commands   — commit·push·PR 자동화"
)

# 선택 배열 초기화
declare -a SELECTED=()
for i in "${!PLUGIN_KEYS[@]}"; do
  SELECTED[$i]="n"
done

echo "설치할 플러그인을 선택하세요."
echo "번호를 입력하면 선택/해제됩니다. (예: 1 3 5)"
echo "전체 선택: a  /  완료: d  /  취소: q"
echo ""

while true; do
  echo "─────────────────────────────────────────────"
  for i in "${!PLUGIN_KEYS[@]}"; do
    if [ "${SELECTED[$i]}" = "y" ]; then
      echo "  [✓] $((i+1)). ${PLUGIN_NAMES[$i]}"
    else
      echo "  [ ] $((i+1)). ${PLUGIN_NAMES[$i]}"
    fi
  done
  echo "─────────────────────────────────────────────"
  echo ""
  read -p "입력: " input

  case "$input" in
    q|Q)
      echo "취소했습니다."
      exit 0
      ;;
    a|A)
      for i in "${!PLUGIN_KEYS[@]}"; do SELECTED[$i]="y"; done
      echo "전체 선택됨"
      ;;
    d|D)
      break
      ;;
    *)
      for num in $input; do
        idx=$((num - 1))
        if [ $idx -ge 0 ] && [ $idx -lt ${#PLUGIN_KEYS[@]} ]; then
          if [ "${SELECTED[$idx]}" = "y" ]; then
            SELECTED[$idx]="n"
          else
            SELECTED[$idx]="y"
          fi
        fi
      done
      ;;
  esac
  echo ""
done

# 선택된 플러그인 확인
INSTALL_LIST=()
for i in "${!PLUGIN_KEYS[@]}"; do
  if [ "${SELECTED[$i]}" = "y" ]; then
    INSTALL_LIST+=("${PLUGIN_KEYS[$i]}")
  fi
done

if [ ${#INSTALL_LIST[@]} -eq 0 ]; then
  echo "선택된 플러그인이 없습니다. 종료합니다."
  exit 0
fi

echo ""
echo "설치할 플러그인:"
for key in "${INSTALL_LIST[@]}"; do
  echo "  - $key"
done
echo ""
read -p "settings.json에 추가하겠습니까? (y/n): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
  echo "취소했습니다."
  exit 0
fi

# settings.json에 enabledPlugins 추가
for key in "${INSTALL_LIST[@]}"; do
  # 이미 있는지 확인
  if python3 -c "
import json, sys
with open('$SETTINGS_FILE') as f:
    d = json.load(f)
plugins = d.get('enabledPlugins', {})
sys.exit(0 if '$key' in plugins else 1)
" 2>/dev/null; then
    echo "  이미 설치됨: $key"
  else
    python3 -c "
import json
with open('$SETTINGS_FILE') as f:
    d = json.load(f)
if 'enabledPlugins' not in d:
    d['enabledPlugins'] = {}
d['enabledPlugins']['$key'] = True
with open('$SETTINGS_FILE', 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
print('  ✅ 설치됨: $key')
"
  fi
done

echo ""
echo "완료! Claude Code를 재시작하면 플러그인이 활성화됩니다."
echo ""
