"""
OTel Debug - Stop Hook
Claude Code Stop 이벤트에서 받는 데이터를 로깅하여 스키마 파악
"""

import json
import os
import sys
from datetime import datetime

LOG_FILE = os.path.expanduser("~/.claude/hooks/otel_stop_debug.json")


def main():
    # stdin에서 hook 데이터 읽기
    stdin_data = ""
    if not sys.stdin.isatty():
        stdin_data = sys.stdin.read()

    # 환경변수 중 CLAUDE/MODEL/OTEL 관련 수집
    env_snapshot = {
        k: v for k, v in os.environ.items()
        if any(keyword in k.upper() for keyword in ["CLAUDE", "MODEL", "OTEL", "ANTHROPIC"])
    }

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "stdin_raw": stdin_data[:5000],  # 최대 5KB
        "stdin_parsed": None,
        "env": env_snapshot,
    }

    # stdin JSON 파싱 시도
    if stdin_data.strip():
        try:
            parsed = json.loads(stdin_data)
            log_entry["stdin_parsed"] = parsed
            # transcript는 너무 크니 키만 저장
            if isinstance(parsed, dict) and "transcript" in parsed:
                log_entry["stdin_parsed"]["transcript"] = f"[{len(parsed['transcript'])} messages]"
        except json.JSONDecodeError:
            log_entry["stdin_parse_error"] = "JSONDecodeError"

    # 기존 로그에 append
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        except (json.JSONDecodeError, IOError):
            logs = []

    logs.append(log_entry)

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False, default=str)


if __name__ == "__main__":
    main()
