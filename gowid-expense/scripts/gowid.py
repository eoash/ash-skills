#!/usr/bin/env python3
"""gowid.py — Gowid API helper for Claude Code skill.

Usage: python3 gowid.py <command> [args]

Commands:
  whoami                          현재 사용자 확인 (git email → Gowid user)
  my-expenses                     내 미제출 경비 조회
  detail <id>                     경비 상세 조회
  submit <id> <purposeId> [--memo M] [--participants P] [--dry-run]
  purposes                        용도 목록
  members                         팀원 목록 (참석자 선택용)
  rules [query]                   자동 분류 규칙 조회

Requires: GOWID_API_KEY environment variable.
No external dependencies — stdlib only (urllib, json, subprocess).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# Windows cp949 방어
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

API_BASE = "https://openapi.gowid.com"
_DEFAULT_KEY = "2a33cb19-f808-45a0-9e16-466a896e278a"
API_KEY = os.environ.get("GOWID_API_KEY", _DEFAULT_KEY)


def _out(obj: dict | list) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _err(msg: str) -> None:
    _out({"error": msg})
    sys.exit(1)


def _api_get(path: str) -> dict:
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={"Authorization": API_KEY},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        _err(f"API {e.code}: {path}")
    except urllib.error.URLError as e:
        _err(f"Network error: {e.reason}")


def _api_put(path: str, body: dict) -> dict | None:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=data,
        headers={
            "Authorization": API_KEY,
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else None
    except urllib.error.HTTPError as e:
        _err(f"API PUT {e.code}: {path}")
    except urllib.error.URLError as e:
        _err(f"Network error: {e.reason}")


def _git_email() -> str:
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return ""


# ── Commands ──────────────────────────────────────────────


def cmd_whoami() -> None:
    email = _git_email()
    if not email:
        _err("git config user.email not set")

    resp = _api_get("/v1/members")
    for m in resp["data"]:
        if m.get("email", "").lower() == email.lower():
            _out({
                "userId": m["userId"],
                "userName": m["userName"],
                "email": m["email"],
                "department": (m.get("department") or {}).get("name", ""),
            })
            return
    _err(f"No user found for {email}")


def cmd_my_expenses() -> None:
    email = _git_email()
    if not email:
        _err("git config user.email not set")

    # 사용자 이름 조회
    members_resp = _api_get("/v1/members")
    user_name = ""
    for m in members_resp["data"]:
        if m.get("email", "").lower() == email.lower():
            user_name = m["userName"]
            break
    if not user_name:
        _err("Could not identify user")

    # 이번 달 1일 기준 cutoff
    cutoff = datetime.now().strftime("%Y%m") + "01"

    # 페이징으로 미제출 경비 전체 조회
    all_expenses: list[dict] = []
    page = 0
    while page <= 50:
        resp = _api_get(f"/v1/expenses/not-submitted?page={page}&size=50")
        content = resp["data"].get("content", [])
        if not content:
            break
        all_expenses.extend(content)
        if resp["data"].get("last", True):
            break
        page += 1

    # 본인 경비만 필터
    my_expenses = []
    for e in all_expenses:
        if e.get("cardUserName") == user_name and e.get("expenseDate", "") >= cutoff:
            card_num = e.get("cardNumber", "") or ""
            my_expenses.append({
                "expenseId": e.get("expenseId"),
                "storeName": e.get("storeName", ""),
                "useAmount": e.get("useAmount", 0),
                "currency": e.get("currency", "KRW"),
                "expenseDate": e.get("expenseDate", ""),
                "expenseTime": e.get("expenseTime", ""),
                "cardNumber": card_num[-4:] if card_num else "",
            })

    my_expenses.sort(key=lambda x: x["expenseDate"], reverse=True)
    _out({"count": len(my_expenses), "expenses": my_expenses})


def cmd_detail(expense_id: str) -> None:
    resp = _api_get(f"/v1/expenses/{expense_id}")
    d = resp["data"]
    card = d.get("card") or {}
    user = card.get("cardUser") or {}
    card_num = card.get("cardNumber", "") or ""
    _out({
        "expenseId": d.get("expenseId"),
        "storeName": d.get("storeName", ""),
        "useAmount": d.get("useAmount", 0),
        "currency": d.get("currency", "KRW"),
        "expenseDate": d.get("expenseDate", ""),
        "expenseTime": d.get("expenseTime", ""),
        "approvalStatus": d.get("approvalStatus", ""),
        "purpose": d.get("purpose") or {},
        "memo": d.get("memo", ""),
        "cardNumber": card_num[-4:] if card_num else "",
        "cardAlias": card.get("alias", ""),
        "userName": user.get("userName", ""),
    })


def cmd_submit(expense_id: str, purpose_id: str,
               memo: str = "", participants: str = "",
               dry_run: bool = False) -> None:
    # 사전 확인
    detail = _api_get(f"/v1/expenses/{expense_id}")
    status = detail["data"].get("approvalStatus", "")
    if status != "NOT_SUBMITTED":
        _out({"error": f"Already {status}", "expenseId": int(expense_id)})
        return

    if dry_run:
        _out({
            "dry_run": True,
            "expenseId": int(expense_id),
            "purposeId": int(purpose_id),
            "memo": memo,
            "participants": participants,
            "status": "would_submit",
        })
        return

    # 메모 설정
    if memo:
        _api_put(f"/v1/expenses/{expense_id}/memo", {"memo": memo})

    # 제출
    body: dict = {"purposeId": int(purpose_id)}
    if participants:
        body["participantIdList"] = [int(p.strip()) for p in participants.split(",") if p.strip()]
    if memo:
        body["memo"] = memo

    _api_put(f"/v1/expenses/{expense_id}", body)
    _out({"success": True, "expenseId": int(expense_id), "purposeId": int(purpose_id), "memo": memo})


def cmd_purposes() -> None:
    resp = _api_get("/v2/purposes?isActivated=true")
    purposes = []
    for p in sorted(resp["data"], key=lambda x: x["name"]):
        purposes.append({
            "purposeId": p["purposeId"],
            "name": p["name"],
            "category": (p.get("category") or {}).get("name", ""),
            "limitAmount": p.get("limitAmount", 0),
            "hasRequirements": len(p.get("requirements", [])) > 0,
        })
    _out(purposes)


def cmd_members() -> None:
    resp = _api_get("/v1/members")
    members = []
    for m in sorted(resp["data"], key=lambda x: x["userName"]):
        if m.get("status") != "NORMAL":
            continue
        members.append({
            "userId": m["userId"],
            "userName": m["userName"],
            "email": m.get("email", ""),
            "department": (m.get("department") or {}).get("name", ""),
        })
    _out(members)


def cmd_rules(query: str = "") -> None:
    rules_file = Path(__file__).resolve().parent.parent / "data" / "auto_rules.json"
    if not rules_file.exists():
        _err("auto_rules.json not found")

    with open(rules_file, encoding="utf-8") as f:
        data = json.load(f)

    rules = data.get("rules", [])
    if query:
        q = query.lower()
        rules = [
            r for r in rules
            if q in r.get("store_pattern", "").lower()
            or q in r.get("purpose_name", "").lower()
        ]

    result = [
        {
            "pattern": r.get("store_pattern", ""),
            "purpose": r.get("purpose_name", ""),
            "memo": r.get("requirement_answer", ""),
            "confidence": r.get("confidence", 0),
        }
        for r in rules[:50]
    ]
    _out({"count": len(rules), "showing": len(result), "rules": result})


# ── Main ──────────────────────────────────────────────────

# API 키 없이 실행 가능한 커맨드
_LOCAL_COMMANDS = {"setup", "rules", "help"}


def cmd_setup() -> None:
    """첫 실행 셋업 가이드."""
    email = _git_email()
    has_key = bool(API_KEY)

    print("=" * 50)
    print("  Gowid 경비 스킬 셋업 가이드")
    print("=" * 50)
    print()

    # Step 1: git email
    if email:
        print(f"[OK] git email: {email}")
    else:
        print("[!!] git config user.email 이 설정되지 않았습니다.")
        print("     git config --global user.email \"your@eoeoeo.net\"")
    print()

    # Step 2: API Key
    print(f"[OK] GOWID_API_KEY 설정됨 ({'환경변수' if os.environ.get('GOWID_API_KEY') else '내장 키'})")
    print()

    # Step 3: 연결 확인
    if has_key and email:
        print("연결 확인 중...")
        try:
            resp = _api_get("/v1/members")
            for m in resp["data"]:
                if m.get("email", "").lower() == email.lower():
                    print(f"[OK] Gowid 사용자 확인: {m['userName']} ({email})")
                    print()
                    print("셋업 완료! Claude Code에서 '내 경비 보여줘'라고 말해보세요.")
                    return
            print(f"[!!] {email} 에 매칭되는 Gowid 사용자가 없습니다.")
            print("     Gowid에 등록된 이메일과 git email이 일치하는지 확인하세요.")
        except SystemExit:
            print("[!!] API 연결 실패 — 키가 올바른지 확인하세요.")
    elif has_key:
        print("git email 설정 후 다시 실행하세요: python3 gowid.py setup")
    else:
        print("API 키 설정 후 다시 실행하세요: python3 gowid.py setup")


def main() -> None:
    args = sys.argv[1:]
    cmd = args[0] if args else "help"

    # API 키 사전 체크 (내장 키가 있으므로 일반적으로 도달하지 않음)
    if cmd not in _LOCAL_COMMANDS and not API_KEY:
        print("API 키 오류. python3 gowid.py setup 을 실행하세요.")
        sys.exit(1)

    if cmd == "setup":
        cmd_setup()
    elif cmd == "whoami":
        cmd_whoami()
    elif cmd == "my-expenses":
        cmd_my_expenses()
    elif cmd == "detail":
        if len(args) < 2:
            _err("Usage: gowid.py detail <expenseId>")
        cmd_detail(args[1])
    elif cmd == "submit":
        if len(args) < 3:
            _err("Usage: gowid.py submit <expenseId> <purposeId> [--memo M] [--participants P] [--dry-run]")
        eid, pid = args[1], args[2]
        memo, participants, dry_run = "", "", False
        i = 3
        while i < len(args):
            if args[i] == "--memo" and i + 1 < len(args):
                memo = args[i + 1]; i += 2
            elif args[i] == "--participants" and i + 1 < len(args):
                participants = args[i + 1]; i += 2
            elif args[i] == "--dry-run":
                dry_run = True; i += 1
            else:
                i += 1
        cmd_submit(eid, pid, memo, participants, dry_run)
    elif cmd == "purposes":
        cmd_purposes()
    elif cmd == "members":
        cmd_members()
    elif cmd == "rules":
        cmd_rules(args[1] if len(args) > 1 else "")
    else:
        print("Usage: gowid.py <command>")
        print()
        print("Commands:")
        print("  setup         첫 실행 셋업 가이드")
        print("  whoami        현재 사용자 확인 (git email → Gowid user)")
        print("  my-expenses   내 미제출 경비 조회")
        print("  detail <id>   경비 상세 조회")
        print("  submit <id> <purposeId> [--memo M] [--participants P] [--dry-run]")
        print("                경비 제출")
        print("  purposes      용도 목록")
        print("  members       팀원 목록 (참석자 선택용)")
        print("  rules [query] 자동 분류 규칙 조회")


if __name__ == "__main__":
    main()
