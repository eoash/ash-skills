"""
EO Studio - SessionStart Hook
역할: 기본 프로젝트 컨텍스트 출력
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path("C:/Users/ash/ash")


def get_git_log():
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            capture_output=True, text=True, encoding="utf-8", cwd=PROJECT_ROOT
        )
        return result.stdout.strip() if result.returncode == 0 else "(git log 실패)"
    except Exception:
        return "(git 없음)"


def main():
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    output = f"""=== EO Studio Session Start | {today} ===

[최근 커밋]
{get_git_log()}
"""
    sys.stdout.buffer.write(output.encode("utf-8"))
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
