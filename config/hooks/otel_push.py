"""
OTel Push - Stop Hook
Claude Code 세션 종료 시 transcript JSONL을 파싱하여
토큰 사용량을 OTel Collector로 push한다.

내장 텔레메트리의 모델명 오보고 버그를 우회하여 정확한 데이터를 전송.
"""

import json
import hashlib
import os
import sys
import urllib.request
import urllib.error
from collections import defaultdict

OTEL_ENDPOINT = "https://otel-collector-production-2dac.up.railway.app"
# Gemini CLI v0.33+ 표준 경로 복원 (v0.32 버그 우회 해제)
OTLP_METRICS_PATH = "/v1/metrics"

# 팀 메타데이터
SERVICE_NAME = "claude-code"
TEAM_NAME = "eostudio"


def parse_transcript(transcript_path: str) -> list[dict]:
    """transcript JSONL에서 assistant 메시지의 model/usage 추출 (message ID 중복 제거)

    Claude Code transcript는 하나의 API 호출에 대해 여러 JSONL 행을 기록
    (thinking block, tool_use block, text block 등). 같은 message.id는
    동일한 usage를 공유하므로 마지막 항목만 사용하여 2-4x 과다집계 방지.
    """
    # message ID별로 마지막 항목만 유지 (last-wins 전략)
    seen: dict[str, dict] = {}
    no_id_entries: list[dict] = []
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if record.get("type") != "assistant":
                    continue

                msg = record.get("message", {})
                model = msg.get("model")
                usage = msg.get("usage")
                if not model or not usage:
                    continue

                msg_id = msg.get("id")
                entry = {"model": model, "usage": usage}
                if msg_id:
                    seen[msg_id] = entry  # 같은 ID는 마지막 값으로 덮어쓰기
                else:
                    no_id_entries.append(entry)
    except (IOError, OSError):
        pass
    return list(seen.values()) + no_id_entries


def count_bash_commands(transcript_path: str):
    """transcript에서 git commit / gh pr create 실행 횟수 카운트 (fallback용)"""
    commits = 0
    prs = 0
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("type") != "assistant":
                    continue
                for block in record.get("message", {}).get("content", []):
                    if block.get("type") == "tool_use" and block.get("name") == "Bash":
                        cmd = block.get("input", {}).get("command", "")
                        if "git commit" in cmd:
                            commits += 1
                        if "gh pr create" in cmd:
                            prs += 1
    except (IOError, OSError):
        pass
    return commits, prs


def count_git_activity(transcript_path: str, user_email: str):
    """git log 기반 세션 중 실제 커밋 카운트.
    transcript 파일 생성 시점 이후의 커밋을 git history에서 직접 조회.
    Claude Code 밖에서 만든 커밋도 포함되므로 전 팀원 커버 가능.
    """
    import subprocess
    import datetime

    # 세션 시작 시간: transcript 파일 생성 시간
    try:
        stat = os.stat(transcript_path)
        start_time = getattr(stat, "st_birthtime", stat.st_ctime)
        start_iso = datetime.datetime.fromtimestamp(start_time).isoformat()
    except Exception:
        return 0

    # git log로 세션 중 커밋 카운트
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"--after={start_iso}", f"--author={user_email}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return len(result.stdout.strip().split("\n"))
    except Exception:
        pass
    return 0


def aggregate_tokens(entries: list[dict]) -> dict:
    """모델별, 토큰 타입별 합산"""
    # key: (model, token_type) -> sum
    totals = defaultdict(int)

    for e in entries:
        model = e["model"]
        usage = e["usage"]

        totals[(model, "input")] += usage.get("input_tokens", 0)
        totals[(model, "output")] += usage.get("output_tokens", 0)
        totals[(model, "cache_read")] += usage.get("cache_read_input_tokens", 0)
        totals[(model, "cache_creation")] += usage.get("cache_creation_input_tokens", 0)

    return dict(totals)


def estimate_cost(totals: dict) -> dict:
    """모델별 비용 추정 (USD). 가격은 2026-03 기준 근사치."""
    # per 1M tokens
    pricing = {
        "claude-opus-4-6": {"input": 15.0, "output": 75.0, "cache_read": 1.5, "cache_creation": 18.75},
        "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_creation": 3.75},
        "claude-haiku-4-5": {"input": 0.8, "output": 4.0, "cache_read": 0.08, "cache_creation": 1.0},
    }
    # fallback: sonnet pricing
    default_price = pricing["claude-sonnet-4-6"]

    costs = defaultdict(float)
    for (model, token_type), count in totals.items():
        price_map = pricing.get(model, default_price)
        rate = price_map.get(token_type, price_map.get("input", 3.0))
        costs[model] += (count / 1_000_000) * rate

    return dict(costs)


def build_otlp_payload(totals: dict, costs: dict, user_email: str, session_id: str, commits: int = 0, prs: int = 0) -> dict:
    """OTLP JSON 형식의 메트릭 payload 생성"""
    import time

    now_ns = int(time.time() * 1e9)

    # 토큰 메트릭 데이터 포인트
    token_data_points = []
    for (model, token_type), count in totals.items():
        if count == 0:
            continue
        token_data_points.append({
            "attributes": [
                {"key": "model", "value": {"stringValue": model}},
                {"key": "token_type", "value": {"stringValue": token_type}},
                {"key": "user_email", "value": {"stringValue": user_email}},
            ],
            "timeUnixNano": str(now_ns),
            "startTimeUnixNano": str(now_ns),
            "asInt": str(count),
        })

    # 비용 메트릭 데이터 포인트
    cost_data_points = []
    for model, cost in costs.items():
        if cost == 0:
            continue
        cost_data_points.append({
            "attributes": [
                {"key": "model", "value": {"stringValue": model}},
                {"key": "user_email", "value": {"stringValue": user_email}},
            ],
            "timeUnixNano": str(now_ns),
            "startTimeUnixNano": str(now_ns),
            "asDouble": round(cost, 6),
        })

    metrics = []
    if token_data_points:
        metrics.append({
            "name": "claude_code_tokens_total",
            "description": "Claude Code token usage per session",
            "sum": {
                "dataPoints": token_data_points,
                "aggregationTemporality": 1,  # DELTA
                "isMonotonic": True,
            },
        })
    if cost_data_points:
        metrics.append({
            "name": "claude_code_cost_total",
            "description": "Claude Code estimated cost per session (USD)",
            "sum": {
                "dataPoints": cost_data_points,
                "aggregationTemporality": 1,
                "isMonotonic": True,
            },
        })

    # 세션 카운트: otel_push.py 1회 실행 = 1 세션
    metrics.append({
        "name": "claude_code_session_count_total",
        "description": "Claude Code session count",
        "sum": {
            "dataPoints": [{
                "attributes": [
                    {"key": "user_email", "value": {"stringValue": user_email}},
                ],
                "timeUnixNano": str(now_ns),
                "startTimeUnixNano": str(now_ns),
                "asInt": "1",
            }],
            "aggregationTemporality": 1,
            "isMonotonic": True,
        },
    })

    if commits > 0:
        metrics.append({
            "name": "claude_code_commit_count_total",
            "description": "Git commits made during Claude Code sessions",
            "sum": {
                "dataPoints": [{
                    "attributes": [
                        {"key": "user_email", "value": {"stringValue": user_email}},
                    ],
                    "timeUnixNano": str(now_ns),
                    "startTimeUnixNano": str(now_ns),
                    "asInt": str(commits),
                }],
                "aggregationTemporality": 1,
                "isMonotonic": True,
            },
        })

    if prs > 0:
        metrics.append({
            "name": "claude_code_pull_request_count_total",
            "description": "Pull requests created during Claude Code sessions",
            "sum": {
                "dataPoints": [{
                    "attributes": [
                        {"key": "user_email", "value": {"stringValue": user_email}},
                    ],
                    "timeUnixNano": str(now_ns),
                    "startTimeUnixNano": str(now_ns),
                    "asInt": str(prs),
                }],
                "aggregationTemporality": 1,
                "isMonotonic": True,
            },
        })

    return {
        "resourceMetrics": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": SERVICE_NAME}},
                        {"key": "team.name", "value": {"stringValue": TEAM_NAME}},
                    ]
                },
                "scopeMetrics": [
                    {
                        "scope": {"name": "claude.code.stop-hook", "version": "1.0.0"},
                        "metrics": metrics,
                    }
                ],
            }
        ]
    }


def push_metrics(payload: dict) -> bool:
    """OTLP HTTP JSON으로 메트릭 전송"""
    url = OTEL_ENDPOINT + OTLP_METRICS_PATH
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return False


EMAIL_ALIAS = {
    "jobskim@icloud.com": "ty@eoeoeo.net",
}


def sanitize_email(email: str) -> str:
    """중복 도메인 제거 + alias 변환 (git email이 다른 팀원용)"""
    at_count = email.count("@")
    if at_count > 1:
        parts = email.split("@")
        email = f"{parts[0]}@{parts[-1]}"
    normalized = email.lower()
    return EMAIL_ALIAS.get(normalized, normalized)


def detect_user_email() -> str:
    """이메일 감지: git config → .otel_email 파일 → unknown"""
    # 1. git config
    try:
        import subprocess
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return sanitize_email(result.stdout.strip())
    except Exception:
        pass
    # 2. install-hook이 저장한 .otel_email 파일
    otel_email_path = os.path.join(os.path.expanduser("~/.claude/hooks"), ".otel_email")
    try:
        if os.path.exists(otel_email_path):
            with open(otel_email_path, "r", encoding="utf-8") as f:
                email = f.read().strip()
            if email:
                return sanitize_email(email)
    except Exception:
        pass
    return "unknown"


SENT_STATE_DIR = os.path.expanduser("~/.claude/hooks/.otel_sent")


def _state_path(transcript_path: str) -> str:
    """transcript 경로를 해시하여 상태 파일 경로 생성"""
    h = hashlib.md5(transcript_path.encode()).hexdigest()[:12]
    return os.path.join(SENT_STATE_DIR, f"{h}.json")


def load_sent_state(transcript_path: str) -> dict:
    """이전 push에서 보낸 토큰 합계 로드. 없으면 빈 dict."""
    path = _state_path(transcript_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, OSError, json.JSONDecodeError):
        return {}


def save_sent_state(transcript_path: str, totals: dict, commits: int = 0, prs: int = 0):
    """현재 토큰 합계를 상태 파일에 저장 (다음 push에서 delta 계산용)"""
    os.makedirs(SENT_STATE_DIR, exist_ok=True)
    path = _state_path(transcript_path)
    # key를 "model|token_type" 문자열로 변환 (JSON 호환)
    serializable = {"_commits": commits, "_prs": prs}
    for (model, token_type), count in totals.items():
        serializable[f"{model}|{token_type}"] = count
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(serializable, f)
    except (IOError, OSError):
        pass


def compute_delta(totals: dict, prev_state: dict) -> dict:
    """현재 합계 - 이전에 보낸 합계 = 실제 delta"""
    delta = {}
    for (model, token_type), count in totals.items():
        key = f"{model}|{token_type}"
        prev = prev_state.get(key, 0)
        diff = count - prev
        if diff > 0:
            delta[(model, token_type)] = diff
    return delta


DAILY_BACKFILL_MARKER = os.path.expanduser("~/.claude/hooks/.backfill_daily")
BACKFILL_SCRIPT_URL = "https://raw.githubusercontent.com/eoash/eoash/main/token-dashboard/scripts/generate_backfill.py"
BACKFILL_API_URL = "https://token-dashboard-iota.vercel.app/api/backfill"


def send_session_backfill(delta: dict, user_email: str):
    """매 세션 종료 시 현재 세션의 delta를 backfill API에 전송.
    backfill cutoff를 항상 오늘로 유지하여 Prometheus 과다집계 영향 차단."""
    import datetime

    if not delta or not user_email:
        return

    today = datetime.date.today().isoformat()

    # delta: {(model, token_type): count} → 날짜+모델별 집계
    by_model = defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0,
                                     "cache_read_tokens": 0, "cache_creation_tokens": 0})
    for (model, token_type), count in delta.items():
        if token_type == "input":
            by_model[model]["input_tokens"] += count
        elif token_type == "output":
            by_model[model]["output_tokens"] += count
        elif token_type == "cache_read":
            by_model[model]["cache_read_tokens"] += count
        elif token_type == "cache_creation":
            by_model[model]["cache_creation_tokens"] += count

    records = []
    for model, tokens in by_model.items():
        records.append({"date": today, "model": model, **tokens})

    if not records:
        return

    try:
        payload = json.dumps({"email": user_email, "data": records, "mode": "add"}).encode("utf-8")
        req = urllib.request.Request(
            BACKFILL_API_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=15)
    except Exception:
        pass  # 실패해도 메인 로직에 영향 없음


def maybe_daily_rebackfill(user_email: str):
    """하루 1회 전체 transcript re-backfill. 누락 보정용 안전망.
    날짜 마커로 오늘 이미 실행했으면 스킵."""
    import datetime

    today = datetime.date.today().isoformat()

    # 오늘 이미 실행했는지 확인
    try:
        if os.path.exists(DAILY_BACKFILL_MARKER):
            with open(DAILY_BACKFILL_MARKER, "r", encoding="utf-8") as f:
                if f.read().strip() == today:
                    return
    except Exception:
        pass

    import subprocess
    import tempfile

    try:
        # 최신 generate_backfill.py 다운로드
        script_path = os.path.join(tempfile.gettempdir(), "generate_backfill_daily.py")
        urllib.request.urlretrieve(BACKFILL_SCRIPT_URL, script_path)

        # 실행하여 backfill JSON 생성 (Windows: python3 없을 수 있으므로 sys.executable 사용)
        out_path = os.path.join(tempfile.gettempdir(), "backfill_daily.json")
        subprocess.run(
            [sys.executable, script_path, "--out", out_path],
            capture_output=True, text=True, timeout=60,
        )

        if not os.path.exists(out_path):
            return

        with open(out_path, "r", encoding="utf-8") as f:
            backfill_data = json.load(f)

        if not backfill_data.get("data"):
            return

        # API에 POST
        backfill_data["email"] = user_email
        payload = json.dumps(backfill_data).encode("utf-8")
        req = urllib.request.Request(
            BACKFILL_API_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 200:
                # 날짜 마커 갱신 — 오늘은 다시 실행 안 함
                os.makedirs(os.path.dirname(DAILY_BACKFILL_MARKER), exist_ok=True)
                with open(DAILY_BACKFILL_MARKER, "w", encoding="utf-8") as m:
                    m.write(today)
    except Exception:
        pass  # 실패해도 메인 로직에 영향 없음
    finally:
        for p in [script_path, out_path]:
            try:
                os.remove(p)
            except Exception:
                pass


def ensure_hook_registered():
    """settings.json에 Stop hook이 등록되어 있는지 확인하고, 없으면 자동 복구.
    otel_push.py는 매 세션 GitHub에서 자동 다운로드되므로,
    이 함수만으로 전 팀원 자가복구가 가능하다 (재설치 불필요)."""
    import platform
    settings_path = os.path.expanduser("~/.claude/settings.json")
    base_url = "https://raw.githubusercontent.com/eoash/eoash/main/token-dashboard/scripts"
    hooks_dir = os.path.expanduser("~/.claude/hooks")
    hook_file = os.path.join(hooks_dir, "otel_push.py")

    if platform.system() == "Windows":
        hook_file_win = hook_file.replace("/", "\\")
        hook_cmd = (
            "powershell -NoProfile -Command \""
            "$env:PYTHONUTF8='1';$env:PYTHONIOENCODING='utf-8';"
            "$d=[Console]::In.ReadToEnd();"
            f"Invoke-WebRequest -Uri '{base_url}/otel_push.py' -OutFile '{hook_file_win}' -ErrorAction SilentlyContinue;"
            f"$d|python3 '{hook_file_win}'\""
        )
    else:
        hook_cmd = (
            "bash -c 'D=$(cat);curl -sL "
            f"{base_url}/otel_push.py -o ~/.claude/hooks/otel_push.py 2>/dev/null;"
            "echo \"$D\"|python3 ~/.claude/hooks/otel_push.py'"
        )

    try:
        data = {}
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        # Stop hook에 otel_push가 있는지 확인 + Windows에서 bash hook 감지 시 교체
        found = False
        needs_replace = False
        for entry in data.get("hooks", {}).get("Stop", []):
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                if "otel_push" in cmd:
                    found = True
                    # Windows인데 bash 명령어가 등록되어 있으면 powershell로 교체
                    if platform.system() == "Windows" and cmd.startswith("bash "):
                        hook["command"] = hook_cmd
                        needs_replace = True
                    break

        if needs_replace:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        if not found:
            if "hooks" not in data:
                data["hooks"] = {}
            if "Stop" not in data["hooks"]:
                data["hooks"]["Stop"] = []
            data["hooks"]["Stop"].append(
                {"hooks": [{"type": "command", "command": hook_cmd}]}
            )
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
    except Exception:
        pass  # 복구 실패해도 메인 로직에 영향 없음


def main():
    # stdin에서 hook 데이터 읽기
    if sys.stdin.isatty():
        return

    stdin_data = sys.stdin.read().strip()
    if not stdin_data:
        return

    try:
        hook_data = json.loads(stdin_data)
    except json.JSONDecodeError:
        return

    transcript_path = hook_data.get("transcript_path")
    session_id = hook_data.get("session_id", "unknown")

    if not transcript_path or not os.path.exists(transcript_path):
        return

    # 0. Hook 자가복구 — settings.json에 Stop hook이 없으면 재등록
    ensure_hook_registered()

    # 1. transcript 파싱
    entries = parse_transcript(transcript_path)
    if not entries:
        return

    # 2. 토큰 합산 (전체 transcript)
    totals = aggregate_tokens(entries)
    if not totals:
        return

    # 3. 이전 push 상태와 비교하여 실제 delta만 추출
    #    resume 시 전체 transcript를 다시 파싱하므로, 이전에 보낸 분을 빼야 이중 집계 방지
    prev_state = load_sent_state(transcript_path)
    delta = compute_delta(totals, prev_state)
    if not delta:
        # 새로운 토큰이 없으면 세션 카운트만 보내고 종료
        save_sent_state(transcript_path, totals)
        return

    # 4. 비용 추정 (delta 기준)
    costs = estimate_cost(delta)

    # 5. 사용자 이메일 (git activity 조회에 필요하므로 먼저 감지)
    user_email = detect_user_email()

    # 6. 커밋/PR 카운트 (delta 계산)
    git_commits = count_git_activity(transcript_path, user_email)
    transcript_commits, total_prs = count_bash_commands(transcript_path)
    total_commits = max(git_commits, transcript_commits)
    prev_commits = prev_state.get("_commits", 0)
    prev_prs = prev_state.get("_prs", 0)
    commits = max(0, total_commits - prev_commits)
    prs = max(0, total_prs - prev_prs)

    # 7. OTLP payload 생성 & 전송 (delta만 전송)
    payload = build_otlp_payload(delta, costs, user_email, session_id, commits, prs)
    success = push_metrics(payload)

    # 8. 전송 성공 시 상태 저장 (실패 시 다음 push에서 재시도)
    if success:
        save_sent_state(transcript_path, totals, total_commits, total_prs)

    # 9. 세션 backfill — 매 세션 delta를 backfill API에도 전송 (Prometheus 과다집계 차단)
    send_session_backfill(delta, user_email)

    # 10. 하루 1회 전체 re-backfill — 누락 보정용 안전망
    maybe_daily_rebackfill(user_email)


if __name__ == "__main__":
    main()
