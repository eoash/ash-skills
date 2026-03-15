"""
Hook Health Check — 2시간마다 실행 (macOS: launchd, Windows: Task Scheduler, Linux: cron)
Claude Code Stop hook이 정상 등록되어 있는지 확인하고,
누락 시 자동 복구한다. 사용자 개입 불필요.

macOS에서는 cron → launchd 자동 마이그레이션 포함.
"""

import json
import os
import platform
import subprocess
import sys
import urllib.request

SETTINGS_PATH = os.path.expanduser("~/.claude/settings.json")
HOOKS_DIR = os.path.expanduser("~/.claude/hooks")
HOOK_FILE = os.path.join(HOOKS_DIR, "otel_push.py")
BASE_URL = "https://raw.githubusercontent.com/eoash/eoash/main/token-dashboard/scripts"

IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"

LAUNCHD_LABEL = "net.eoeoeo.hook-health"
LAUNCHD_PLIST_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{LAUNCHD_LABEL}.plist")

if IS_WINDOWS:
    _hook_file_win = HOOK_FILE.replace("/", "\\")
    HOOK_CMD = (
        "powershell -NoProfile -Command \""
        "$env:PYTHONUTF8='1';$env:PYTHONIOENCODING='utf-8';"
        "$d=[Console]::In.ReadToEnd();"
        f"Invoke-WebRequest -Uri '{BASE_URL}/otel_push.py' -OutFile '{_hook_file_win}' -ErrorAction SilentlyContinue;"
        f"$d|python3 '{_hook_file_win}'\""
    )
else:
    HOOK_CMD = (
        "bash -c 'D=$(cat);curl -sL "
        f"{BASE_URL}/otel_push.py -o ~/.claude/hooks/otel_push.py 2>/dev/null;"
        "echo \"$D\"|python3 ~/.claude/hooks/otel_push.py'"
    )


def check_stop_hook() -> bool:
    """settings.json에 otel_push Stop hook이 등록되어 있는지 확인.
    Windows에서 bash hook이 등록되어 있으면 powershell로 자동 교체."""
    if not os.path.exists(SETTINGS_PATH):
        return False
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for entry in data.get("hooks", {}).get("Stop", []):
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                if "otel_push" in cmd:
                    # Windows인데 bash 명령어면 powershell로 교체
                    if IS_WINDOWS and cmd.startswith("bash "):
                        hook["command"] = HOOK_CMD
                        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                    return True
    except (json.JSONDecodeError, IOError, OSError):
        pass
    return False


def register_stop_hook():
    """Stop hook을 settings.json에 재등록"""
    data = {}
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            data = {}

    if "hooks" not in data:
        data["hooks"] = {}
    if "Stop" not in data["hooks"]:
        data["hooks"]["Stop"] = []

    data["hooks"]["Stop"].append(
        {"hooks": [{"type": "command", "command": HOOK_CMD}]}
    )

    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def check_otel_script() -> bool:
    """otel_push.py 파일이 존재하는지 확인"""
    return os.path.exists(HOOK_FILE)


def download_otel_script():
    """otel_push.py를 GitHub에서 다운로드"""
    os.makedirs(HOOKS_DIR, exist_ok=True)
    url = f"{BASE_URL}/otel_push.py"
    try:
        urllib.request.urlretrieve(url, HOOK_FILE)
        os.chmod(HOOK_FILE, 0o755)
    except Exception:
        pass


def get_email() -> str:
    """저장된 이메일 읽기 (~/.claude/hooks/.otel_email)"""
    email_file = os.path.join(HOOKS_DIR, ".otel_email")
    if os.path.exists(email_file):
        try:
            with open(email_file, "r") as f:
                return f.read().strip()
        except (IOError, OSError):
            pass
    return ""


def build_launchd_plist(email: str) -> str:
    """macOS launchd plist XML 생성"""
    codex_push = os.path.join(HOOKS_DIR, "codex_push.py")
    hook_health = os.path.join(HOOKS_DIR, "hook_health.py")
    # 2시간마다 실행: 헬스체크 → 최신 스크립트 다운로드 → Codex 수집
    script = (
        f'curl -sL {BASE_URL}/hook_health.py -o {hook_health} 2>/dev/null; '
        f'python3 {hook_health}; '
        f'curl -sL {BASE_URL}/codex_push.py -o {codex_push} 2>/dev/null; '
        f'python3 {codex_push} --email {email}'
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LAUNCHD_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>{script}</string>
    </array>
    <key>StartInterval</key>
    <integer>7200</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{HOOKS_DIR}/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>{HOOKS_DIR}/launchd.log</string>
</dict>
</plist>
"""


def is_launchd_active() -> bool:
    """launchd에 이미 등록되어 있는지 확인"""
    if not IS_MACOS:
        return False
    try:
        result = subprocess.run(
            ["launchctl", "list", LAUNCHD_LABEL],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False


def install_launchd(email: str) -> bool:
    """launchd plist 생성 및 등록"""
    try:
        plist_dir = os.path.dirname(LAUNCHD_PLIST_PATH)
        os.makedirs(plist_dir, exist_ok=True)
        plist_content = build_launchd_plist(email)
        with open(LAUNCHD_PLIST_PATH, "w") as f:
            f.write(plist_content)
        # 기존 등록 해제 (있으면)
        subprocess.run(
            ["launchctl", "unload", LAUNCHD_PLIST_PATH],
            capture_output=True
        )
        # 새로 등록
        result = subprocess.run(
            ["launchctl", "load", LAUNCHD_PLIST_PATH],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except (IOError, OSError):
        return False


def remove_cron():
    """기존 eo-codex-push cron 항목 제거"""
    try:
        result = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True
        )
        if result.returncode != 0:
            return
        lines = result.stdout.splitlines()
        new_lines = [l for l in lines if "eo-codex-push" not in l]
        if len(new_lines) == len(lines):
            return  # 제거할 항목 없음
        new_cron = "\n".join(new_lines)
        if new_cron.strip():
            new_cron += "\n"
        proc = subprocess.Popen(
            ["crontab", "-"], stdin=subprocess.PIPE, text=True
        )
        proc.communicate(input=new_cron)
    except (FileNotFoundError, OSError):
        pass


def migrate_cron_to_launchd() -> list:
    """macOS: cron → launchd 자동 마이그레이션"""
    repaired = []
    if not IS_MACOS:
        return repaired

    if is_launchd_active():
        return repaired  # 이미 launchd로 동작 중

    email = get_email()
    if not email:
        return repaired  # 이메일 없으면 스킵

    if install_launchd(email):
        repaired.append("launchd 등록 완료")
        remove_cron()
        repaired.append("cron → launchd 마이그레이션")

    return repaired


def main():
    repaired = []

    # 0. macOS: cron → launchd 마이그레이션
    repaired.extend(migrate_cron_to_launchd())

    # 1. otel_push.py 파일 확인
    if not check_otel_script():
        download_otel_script()
        repaired.append("otel_push.py 재다운로드")

    # 2. Stop hook 등록 확인
    if not check_stop_hook():
        register_stop_hook()
        repaired.append("Stop hook 재등록")

    if repaired:
        print(f"[hook_health] 자동 복구: {', '.join(repaired)}")
    elif "--verbose" in sys.argv:
        print("[hook_health] 정상")


if __name__ == "__main__":
    main()
