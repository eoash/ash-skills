"""
EO Studio - Skill Auto-Activation Hook (UserPromptSubmit)
역할: 사용자 프롬프트를 분석해서 관련 스킬을 Claude 컨텍스트에 추천
"""

import json
import re
import sys
from pathlib import Path

RULES_FILE = Path(__file__).parent / "skill-rules.json"
SESSION_LOG = Path(__file__).parent / "skill-activation-log.json"


def load_rules():
    if not RULES_FILE.exists():
        return {}
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("skills", {})


def load_session_log():
    if not SESSION_LOG.exists():
        return {"recommended": []}
    try:
        with open(SESSION_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        return {"recommended": []}


def save_session_log(log):
    with open(SESSION_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False)


def match_skill(prompt, rule):
    prompt_lower = prompt.lower()
    score = 0

    # 1. URL 패턴 매칭 (최우선)
    for pattern in rule.get("urlPatterns", []):
        if re.search(pattern, prompt, re.IGNORECASE):
            score += 10
            return score

    # 2. 키워드 매칭
    for kw in rule.get("keywords", []):
        if kw.lower() in prompt_lower:
            score += 5

    # 3. 의도 패턴 매칭
    for pattern in rule.get("intentPatterns", []):
        if re.search(pattern, prompt, re.IGNORECASE):
            score += 3

    return score


def main():
    # stdin에서 프롬프트 읽기
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    prompt = data.get("prompt", "")
    if not prompt or len(prompt) < 2:
        sys.exit(0)

    # 슬래시 커맨드는 이미 직접 호출이므로 스킵
    if prompt.strip().startswith("/"):
        sys.exit(0)

    # 시스템 태그 제거 (false positive 방지)
    prompt = re.sub(r"<system-reminder>.*?</system-reminder>", "", prompt, flags=re.DOTALL)
    prompt = re.sub(r"<task-notification>.*?</task-notification>", "", prompt, flags=re.DOTALL)
    prompt = re.sub(r"<[^>]+>.*?</[^>]+>", "", prompt, flags=re.DOTALL)
    prompt = prompt.strip()
    if not prompt or len(prompt) < 2:
        sys.exit(0)

    rules = load_rules()
    if not rules:
        sys.exit(0)

    # 매칭 실행
    matches = []
    for skill_name, rule in rules.items():
        score = match_skill(prompt, rule)
        if score > 0:
            matches.append((skill_name, score, rule.get("description", "")))

    if not matches:
        sys.exit(0)

    # 점수 순 정렬
    matches.sort(key=lambda x: x[1], reverse=True)

    # 중복 추천 방지: 이번 세션에서 이미 추천한 스킬 제외
    session_log = load_session_log()
    already = set(session_log.get("recommended", []))
    new_matches = [(name, score, desc) for name, score, desc in matches if name not in already]

    if not new_matches:
        sys.exit(0)

    # 최대 3개까지 추천
    top = new_matches[:3]

    # 세션 로그 업데이트
    for name, _, _ in top:
        session_log.setdefault("recommended", []).append(name)
    save_session_log(session_log)

    # 출력 (Claude 컨텍스트에 주입됨)
    lines = []
    lines.append("[SKILL 자동 추천]")
    for name, score, desc in top:
        lines.append(f"  -> {name}: {desc}")
    lines.append("필요하면 Skill 도구로 해당 스킬을 실행하세요.")

    output = "\n".join(lines)
    sys.stdout.buffer.write(output.encode("utf-8"))
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
