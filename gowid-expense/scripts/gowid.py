#!/usr/bin/env python3
"""gowid.py — Gowid API helper for Claude Code / Codex skill.

Usage: python3 gowid.py <command> [args]

Commands:
  setup                           첫 실행 셋업 가이드
  whoami                          현재 사용자 확인 (GOWID_EMAIL 또는 git email → Gowid 재직 사용자)
  my-expenses [--month YYYYMM]    본인 미제출 경비 조회 (기본: 이번 달, 전체 페이지)
  detail <id>                     본인 경비 상세 조회
  submit <id> <purposeId> [옵션]  본인 미제출 경비 제출
  update <id> <purposeId> [옵션]  본인 SUBMITTED 건 변경 (지정하지 않은 필드는 기존 값 유지)
  suggest <id>                    auto_rules 기반 용도 추천 (본인 경비만)
  purposes                        활성 용도 목록 (필수항목 포함)
  purpose-requirements <purposeId>
  members                         재직 팀원 목록 (참석자 선택용)
  rules [query]                   자동 분류 규칙 조회

submit/update 옵션:
  --memo M                 메모 (IT서비스·멤버십·매거진은 서비스명 칸이 비어 있으면 그 칸으로 이동)
  --participants "id,id"   내부 참석자 userId
  --external "이름:소속,이름"  외부 참석자
  --requirements JSON      필수항목 {"<요구항목id>": ["답"]}
  --clear-memo / --clear-participants / --clear-external   기존 값을 명시적으로 지움
  --confirm-solo           한도 초과 식비를 참석자 없이 본인 단독으로 제출함을 확인
  --dry-run                서버에 쓰지 않고 보낼 내용과 검사 결과만 출력

보안 한계: 이 헬퍼가 쓰는 Gowid API 키는 회사 공용 키다. 본인 확인(이메일→userId)과
소유자 검사는 로컬 CLI의 안전장치일 뿐 인증이 아니다. 키를 가진 사람은 이 스크립트를
거치지 않고 API를 직접 호출할 수 있다. 진짜 본인 제한은 서버측 중계나 사용자별 자격증명이 필요하다.

Requires: GOWID_API_KEY environment variable. stdlib only.
"""
from __future__ import annotations

import calendar
import json
import os
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# Windows cp949 방어
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

_DEFAULT_API_BASE = "https://openapi.gowid.com"
API_KEY = os.environ.get("GOWID_API_KEY", "").strip()

PAGE_SIZE = 100            # /v2/expense-statements 최대 size
MAX_PAGES = 1000           # 안전 상한. 도달하면 조용히 자르지 않고 오류로 중단
SERVICE_NAME_PURPOSES = {12532, 70602, 12536}   # IT서비스, 멤버십, 매거진: 서비스명 칸
MEAL_PURPOSES = {12556, 12555}                  # 점심/야근 — 시각 기준은 회사 정책 미확정
# auto_rules에 있는 자리표시 답. 사실 값이 아니므로 필수항목 답으로 쓰지 않는다.
PLACEHOLDER_ANSWERS = {"IT서비스 정기결제", "업무 이동", "출장", "식비", "소모품"}
_FOREIGN_ENTITY_PREFIXES = ("US-", "미국법인")


def _api_base() -> str:
    """테스트용 GOWID_API_BASE는 로컬 주소만 허용한다(공용 키를 외부로 보내지 않기 위해)."""
    override = os.environ.get("GOWID_API_BASE", "").strip()
    if not override:
        return _DEFAULT_API_BASE
    host = urllib.parse.urlparse(override).hostname or ""
    if host not in ("127.0.0.1", "localhost"):
        _err("GOWID_API_BASE는 테스트용 로컬 주소(127.0.0.1/localhost)만 허용됩니다.")
    return override.rstrip("/")


def _timeout() -> float:
    try:
        return float(os.environ.get("GOWID_HTTP_TIMEOUT", "30"))
    except ValueError:
        return 30.0


def _out(obj: dict | list) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _err(msg: str, code: int = 1, **extra) -> None:
    _out({"error": msg, **extra})
    sys.exit(code)


_HTTP_MESSAGES = {
    400: "요청 데이터가 잘못되었습니다. 필수 항목(purposeRequirementAnswerMap)이 누락되었을 수 있습니다.",
    401: "API 키가 만료되었거나 잘못되었습니다. 운영팀(ash@eoeoeo.net)에 문의하세요.",
    403: "접근 권한이 없습니다. Gowid 계정 상태를 확인하세요.",
    404: "요청한 데이터를 찾을 수 없습니다. ID를 다시 확인하세요.",
    429: "API 요청이 너무 많습니다. 잠시 후 다시 시도하세요.",
    500: "Gowid 서버 오류입니다. 잠시 후 다시 시도하세요.",
}


class ApiError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _request(method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Authorization": API_KEY}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{_api_base()}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=_timeout()) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        msg = _HTTP_MESSAGES.get(e.code, f"HTTP {e.code} 오류")
        raise ApiError(f"{msg} ({method} {path})", e.code)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        reason = getattr(e, "reason", e)
        raise ApiError(f"네트워크 연결 실패/시간 초과: {reason} ({method} {path})")
    if not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise ApiError(f"응답이 JSON이 아닙니다 ({method} {path})")


def _api_get(path: str) -> dict:
    try:
        resp = _request("GET", path)
    except ApiError as e:
        _err(str(e))
    if not isinstance(resp, dict) or "data" not in resp or resp["data"] is None:
        _err(f"응답에 data가 없습니다 (GET {path})")
    return resp


def _data(path: str):
    return _api_get(path)["data"]


def _git_email() -> tuple[str, str]:
    """(email, source). GOWID_EMAIL이 우선한다 — 편의 설정일 뿐 인증이 아니다."""
    env_email = os.environ.get("GOWID_EMAIL", "").strip()
    if env_email:
        return env_email, "GOWID_EMAIL"
    try:
        result = subprocess.run(["git", "config", "user.email"],
                                capture_output=True, text=True, timeout=5)
        return result.stdout.strip(), "git config user.email"
    except Exception:
        return "", ""


def _int_arg(value: str, label: str) -> int:
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        _err(f"{label}는 숫자여야 합니다: {value!r}")
    if n <= 0:
        _err(f"{label}는 양수여야 합니다: {value!r}")
    return n


# ── 본인 식별 / 소유자 검사 ──────────────────────────────


_MEMBERS_CACHE: list[dict] | None = None


def _members() -> list[dict]:
    global _MEMBERS_CACHE
    if _MEMBERS_CACHE is None:
        _MEMBERS_CACHE = _data("/v1/members")
    return _MEMBERS_CACHE


def _resolve_me() -> dict:
    email, source = _git_email()
    if not email:
        _err("본인 이메일을 알 수 없습니다. git config user.email 또는 GOWID_EMAIL을 설정하세요.")
    members = _members()
    matches = [m for m in members if (m.get("email") or "").strip().lower() == email.lower()]
    if not matches:
        _err(f"{email} 에 매칭되는 Gowid 사용자가 없습니다. 등록 이메일을 확인하세요.")
    if len(matches) > 1:
        _err(f"{email} 에 매칭되는 Gowid 사용자가 여러 명이라 본인을 확정할 수 없습니다.")
    me = matches[0]
    if me.get("status") != "NORMAL":
        _err("재직(NORMAL) 상태가 아닌 Gowid 계정입니다. 이 헬퍼로 조회/제출할 수 없습니다.",
             status=me.get("status"))
    if me.get("userId") is None:
        _err("Gowid 사용자 ID를 확인할 수 없습니다.")
    me = dict(me)
    me["_identitySource"] = source
    return me


def _owner_of(detail: dict) -> tuple[str, object] | None:
    """경비 소유자. 실제 /v2/expenses/{id}의 user·card.cardUser에는 userId가 없고
    email·userName·status·isActivated만 온다(2026-11-13 확인) → 보통 이메일로 판정한다.
    userId가 오는 응답이면 userId를 우선한다."""
    card = detail.get("card") or {}
    candidates = [detail.get("user") or {}, card.get("cardUser") or {}]
    for u in candidates:
        if u.get("userId") is not None:
            return "userId", int(u["userId"])
    for u in candidates:
        if u.get("email"):
            return "email", str(u["email"]).strip().lower()
    return None


def _is_owner(detail: dict, me: dict) -> bool:
    owner = _owner_of(detail)
    if owner is None:
        return False
    kind, value = owner
    if kind == "userId":
        return value == int(me["userId"])
    return value == (me.get("email") or "").strip().lower()


def _owned_detail(expense_id: int, me: dict) -> dict:
    detail = _data(f"/v2/expenses/{expense_id}")
    if _owner_of(detail) is None:
        _err("경비 소유자를 확인할 수 없어 차단했습니다.", expenseId=expense_id)
    if not _is_owner(detail, me):
        _err("본인 경비가 아닙니다. 이 헬퍼는 본인 카드 경비만 다룹니다.", expenseId=expense_id)
    return detail


# ── 취소/금액 (원천 필드 기준, 다른 거래와 금액 상쇄 추론은 하지 않음) ──


def _num(v) -> float | None:
    try:
        return float(v) if v is not None and v != "" else None
    except (TypeError, ValueError):
        return None


def _source_void_state(row: dict) -> str | None:
    """원천 레코드 자체의 필드만 본다. 다른 거래와의 ± 짝짓기는 절대 하지 않는다."""
    if row.get("isRefund") is True:
        return "refund"
    for key in ("krwAmount", "useAmount"):
        v = _num(row.get(key))
        if v is not None and v <= 0:
            return "voided"
    if "가승인" in (row.get("storeName") or ""):
        return "preauthorized"
    return None


def _amount_krw(row: dict) -> float | None:
    """원화 금액. krwAmount가 있으면 그것, 없으면 통화가 KRW일 때만 useAmount.
    외화(USD/VND/JPY 등) useAmount는 원화가 아니므로 대입하지 않고 None(확인 필요)."""
    krw = _num(row.get("krwAmount"))
    if krw is not None:
        return krw
    if (row.get("currency") or "KRW").upper() == "KRW":
        return _num(row.get("useAmount"))
    return None


# ── 월/페이지 ─────────────────────────────────────────────


def _month_range(month: str) -> tuple[str, str, str]:
    if month:
        m = re.fullmatch(r"(\d{4})-?(0[1-9]|1[0-2])", month.strip())
        if not m:
            _err(f"--month 형식이 잘못되었습니다: {month!r} (예: 202603 또는 2026-03)")
        y, mo = int(m.group(1)), int(m.group(2))
        if not 2000 <= y <= 2100:
            _err(f"--month 연도 범위가 잘못되었습니다: {month!r} (2000~2100)")
    else:
        now = datetime.now()
        y, mo = now.year, now.month
    last_day = calendar.monthrange(y, mo)[1]
    ym = f"{y}{mo:02d}"
    # /v2/expense-statements startDate/endDate는 양끝 포함으로 문서화되어 있다(eo-portal gowid.ts).
    # 서버 해석이 달라도 결과가 섞이지 않도록 expenseDate로 한 번 더 거른다.
    return ym, f"{ym}01", f"{ym}{last_day:02d}"


def _fetch_all_statements(start: str, end: str) -> list[dict]:
    rows: list[dict] = []
    page = 0
    while True:
        if page >= MAX_PAGES:
            _err(f"페이지 안전 상한({MAX_PAGES})에 도달했습니다. 결과가 잘렸을 수 있어 중단합니다.")
        data = _data(f"/v2/expense-statements?page={page}&size={PAGE_SIZE}"
                     f"&sort=expenseDate,desc&startDate={start}&endDate={end}")
        content = data.get("content") or []
        rows.extend(content)
        total_pages = data.get("totalPages")
        if data.get("last") is True:
            break
        if isinstance(total_pages, int) and page + 1 >= total_pages:
            break
        if not content:
            break
        page += 1
    return rows


# ── Commands ──────────────────────────────────────────────


def cmd_whoami() -> None:
    me = _resolve_me()
    _out({
        "userId": me["userId"],
        "userName": me.get("userName", ""),
        "email": me.get("email", ""),
        "department": (me.get("department") or {}).get("name", ""),
        "identitySource": me["_identitySource"],
        "note": "로컬 이메일 기반 식별이며 인증이 아닙니다. 공용 API 키 자체는 본인 제한을 강제하지 않습니다.",
    })


def cmd_my_expenses(month: str = "") -> None:
    me = _resolve_me()
    ym, start, end = _month_range(month)
    rows = _fetch_all_statements(start, end)

    out_of_range = 0
    void_rows = 0
    unnamed_card_rows = 0
    candidates = []
    for r in rows:
        if str(r.get("expenseDate") or "")[:6] != ym:
            out_of_range += 1
            continue
        if r.get("approvalStatus") != "NOT_SUBMITTED":
            continue
        if _source_void_state(r):
            void_rows += 1
            continue
        card_user = r.get("cardUserName") or ""
        if not card_user:
            unnamed_card_rows += 1
            continue
        if card_user != me.get("userName"):
            continue
        candidates.append(r)

    # 이름 일치는 1차 후보일 뿐 — 상세의 소유자 ID로 확정하고 원천 순액을 다시 본다.
    expenses = []
    owner_mismatch = 0
    void_by_detail = 0
    stale = 0
    for r in candidates:
        d = _data(f"/v2/expenses/{r.get('expenseId')}")
        if not _is_owner(d, me):
            owner_mismatch += 1
            continue
        if d.get("approvalStatus") != "NOT_SUBMITTED":
            stale += 1
            continue
        state = _source_void_state(d)
        if state:
            void_by_detail += 1
            continue
        purpose = d.get("purpose") or r.get("purpose") or {}
        expenses.append({
            "expenseId": r.get("expenseId"),
            "storeName": d.get("storeName") or r.get("storeName", ""),
            "storeAddress": d.get("storeAddress") or r.get("storeAddress", ""),
            "useAmount": d.get("useAmount", r.get("useAmount", 0)),
            "krwAmount": d.get("krwAmount", r.get("krwAmount", 0)),
            "statementKrwAmount": r.get("krwAmount", 0),
            "amountChangedAtSource": _num(d.get("krwAmount")) != _num(r.get("krwAmount")),
            "currency": d.get("currency") or r.get("currency", "KRW"),
            "expenseDate": r.get("expenseDate", ""),
            "expenseTime": r.get("expenseTime", ""),
            "cardNumber": r.get("shortCardNumber") or "",
            "purpose": purpose.get("name", ""),
            "memo": d.get("memo") or r.get("memo") or "",
            "participantCount": r.get("participantCount", 0),
            "requirementAnswers": d.get("purposeRequirementAnswers", r.get("purposeRequirementAnswers", [])),
        })

    _out({
        "month": ym,
        "count": len(expenses),
        "pagesComplete": True,
        "statementRows": len(rows),
        "excluded": {
            "sourceVoidOrRefundRows": void_rows,
            "voidByDetail": void_by_detail,
            "ownerMismatchSameName": owner_mismatch,
            "statusChangedSinceList": stale,
            "outOfMonthRows": out_of_range,
            "unnamedCardRows": unnamed_card_rows,
        },
        "notes": ([f"카드 사용자명이 비어 있는 미제출 {unnamed_card_rows}건은 본인 여부를 확정할 수 없어 표시하지 않았습니다. Gowid 웹에서 카드 별칭을 확인하세요."]
                  if unnamed_card_rows else []),
        "expenses": expenses,
    })


def cmd_detail(expense_id: str) -> None:
    eid = _int_arg(expense_id, "expenseId")
    me = _resolve_me()
    d = _owned_detail(eid, me)
    card = d.get("card") or {}
    user = d.get("user") or card.get("cardUser") or {}
    card_num = card.get("cardNumber", "") or ""
    _out({
        "expenseId": d.get("expenseId"),
        "storeName": d.get("storeName", ""),
        "storeAddress": d.get("storeAddress", ""),
        "useAmount": d.get("useAmount", 0),
        "krwAmount": d.get("krwAmount", 0),
        "currency": d.get("currency", "KRW"),
        "expenseDate": d.get("expenseDate", ""),
        "expenseTime": d.get("expenseTime", ""),
        "approvalStatus": d.get("approvalStatus", ""),
        "sourceState": _source_void_state(d),
        "purpose": d.get("purpose") or {},
        "memo": d.get("memo", ""),
        "cardNumber": card_num[-4:] if card_num else "",
        "cardAlias": card.get("alias", ""),
        "userName": user.get("userName", ""),
        # 실제 참석자 객체에는 전화번호 등 불필요한 개인정보가 있어 이름·이메일만 출력한다.
        "participants": [{"userName": u.get("userName", ""), "email": u.get("email", "")}
                         for u in d.get("participants") or [] if isinstance(u, dict)],
        "external": d.get("expenseExternalUsers") or [],
        "requirementAnswers": d.get("purposeRequirementAnswers", []),
        "comments": d.get("comments", []),
    })


def _parse_external(external: str) -> list[dict]:
    """'이름:회사,이름' → [{"name": 이름, "company": 회사}] (회사는 생략 가능)."""
    users = []
    for item in external.split(","):
        item = item.strip()
        if not item:
            continue
        name, _, company = item.partition(":")
        if not name.strip():
            _err(f"--external 항목에 이름이 없습니다: {item!r}")
        users.append({"name": name.strip(), "company": company.strip()})
    return users


def _parse_requirements(raw: str) -> dict[str, list[str]]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        _err("--requirements 값이 올바른 JSON이 아닙니다. 예: '{\"126\": [\"서울역\"]}'")
    if not isinstance(parsed, dict):
        _err("--requirements는 {\"요구항목id\": [\"답\"]} 형태여야 합니다.")
    out: dict[str, list[str]] = {}
    for k, v in parsed.items():
        key = str(_int_arg(k, "필수항목 id"))
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, list) or not v or not all(isinstance(x, str) and x.strip() for x in v):
            _err(f"필수항목 {key}의 답은 비어 있지 않은 문자열 목록이어야 합니다.")
        out[key] = [x.strip() for x in v]
    return out


def _active_purposes() -> dict[int, dict]:
    return {int(p["purposeId"]): p for p in _data("/v2/purposes?isActivated=true")}


def _purpose_catalog() -> list[dict]:
    """활성·비활성을 포함한 전체 용도 목록(이름 중복 판정용)."""
    return [p for p in _data("/v2/purposes") if p.get("purposeId") is not None]


def _same_category(saved_cat: dict, cat: dict) -> bool | None:
    """True/False, 비교 근거가 없으면 None."""
    if saved_cat.get("categoryId") is not None and cat.get("categoryId") is not None:
        return str(saved_cat["categoryId"]) == str(cat["categoryId"])
    if saved_cat.get("name") and cat.get("name"):
        return str(saved_cat["name"]).strip() == str(cat["name"]).strip()
    return None


def _resolve_saved_purpose(saved: dict | None, catalog: list[dict]) -> tuple[int | None, str | None]:
    """경비에 저장된 용도 → (purposeId, 문제).
    실제 경비 상세의 purpose에는 purposeId가 없고 name·isActivated·hasRequirement·limitAmount·
    limitType·category{categoryId,name}만 온다. ID가 있으면 ID를 쓰고, 없으면 전체 용도 목록에서
    이름 + 카테고리(+활성 여부)가 정확히 하나로 맞을 때만 인정한다. 이름만으로는 판정하지 않는다."""
    if not saved:
        return None, "저장된 용도 없음"
    if saved.get("purposeId") is not None:
        try:
            return int(saved["purposeId"]), None
        except (TypeError, ValueError):
            return None, "purposeId 형식 오류"
    name = (saved.get("name") or "").strip()
    saved_cat = saved.get("category") or {}
    if not name:
        return None, "용도 이름 없음"
    if saved_cat.get("categoryId") is None and not saved_cat.get("name"):
        return None, "용도 카테고리 정보가 없어 이름만으로 확정하지 않음"
    cands = []
    for p in catalog:
        if (p.get("name") or "").strip() != name:
            continue
        if _same_category(saved_cat, p.get("category") or {}) is not True:
            continue
        if isinstance(saved.get("isActivated"), bool) and isinstance(p.get("isActivated"), bool) \
                and saved["isActivated"] != p["isActivated"]:
            continue
        cands.append(p)
    if len(cands) == 1:
        return int(cands[0]["purposeId"]), None
    if not cands:
        return None, f"용도 목록에서 '{name}'(카테고리 일치)를 찾지 못함"
    return None, f"용도 '{name}'가 같은 카테고리에 {len(cands)}개라 불명확"


def _existing_answers(detail: dict, reqs: list[dict] | None = None) -> dict[str, list[str]]:
    """저장된 답을 {요구항목id: [답]}으로.
    실제 형태: [{purposeRequirementId:int, purposeRequirementName:str, answers:[str]}] (2026-11-13 확인).
    구형 {id, item, answer}도 받는다. 용도의 요구항목 목록이 주어지면 id가 그 목록에 없을 때
    항목명으로 대응시키고, 그래도 없으면 버린다."""
    req_ids = {str(r["id"]) for r in reqs or []}
    by_item = {(r.get("item") or "").strip(): str(r["id"]) for r in reqs or [] if r.get("item")}
    out = {}
    for a in detail.get("purposeRequirementAnswers") or []:
        if not isinstance(a, dict):
            continue
        rid = a.get("purposeRequirementId", a.get("id"))
        rname = a.get("purposeRequirementName", a.get("item"))
        key = str(rid) if rid is not None else None
        if reqs is not None and key not in req_ids:
            key = by_item.get((rname or "").strip())
        if key is None:
            continue
        ans = a.get("answers", a.get("answer"))
        if isinstance(ans, str):
            ans = [ans]
        ans = [x for x in (ans or []) if isinstance(x, str) and x.strip()]
        if ans:
            out[key] = ans
    return out


def _participant_ids(detail: dict) -> tuple[list[int], int]:
    """저장된 내부 참석자 → (userId 목록, 확인 못 한 수).
    userId가 없으면(실제 사용자 객체는 email·userName·status만 오는 형태) 이메일로 멤버 목록에서
    정확히 한 명일 때만 userId로 바꾼다. 못 찾거나 이메일이 중복이면 '확인 못 함'으로 센다."""
    raw = detail.get("participants") or []
    if not raw:
        return [], 0
    by_email: dict[str, list[int]] = {}
    for m in _members():
        e = (m.get("email") or "").strip().lower()
        if e and m.get("userId") is not None:
            by_email.setdefault(e, []).append(int(m["userId"]))
    ids, unresolved = [], 0
    for u in raw:
        if not isinstance(u, dict):
            unresolved += 1
            continue
        if u.get("userId") is not None:
            ids.append(int(u["userId"]))
            continue
        hit = by_email.get((u.get("email") or "").strip().lower(), [])
        if len(hit) == 1:
            ids.append(hit[0])
        else:
            unresolved += 1
    return ids, unresolved


def _external_users(detail: dict) -> tuple[list[dict], int]:
    """저장된 외부 참석자 → ([{name, company}], 해석 못 한 수).
    실제 항목 형태는 아직 관측되지 않았다. name이 없는 등 모르는 형태는 건너뛰지 않고 센다."""
    out, unknown = [], 0
    for u in detail.get("expenseExternalUsers") or []:
        if isinstance(u, dict) and isinstance(u.get("name"), str) and u["name"].strip():
            out.append({"name": u["name"].strip(), "company": (u.get("company") or "").strip()})
        else:
            unknown += 1
    return out, unknown


def _postcondition(saved: dict, expected: dict, reqs: list[dict], catalog: list[dict]) -> list[str]:
    problems = []
    if saved.get("approvalStatus") != "SUBMITTED":
        problems.append(f"status={saved.get('approvalStatus')!r} (기대 SUBMITTED)")
    saved_pid, why = _resolve_saved_purpose(saved.get("purpose"), catalog)
    if saved_pid is None:
        problems.append(f"저장된 용도 확인 불가: {why}")
    elif saved_pid != expected["purposeId"]:
        problems.append(f"용도 불일치: 저장 {saved_pid} (기대 {expected['purposeId']})")
    if (saved.get("memo") or "") != (expected.get("memo") or ""):
        problems.append("memo 불일치")
    saved_answers = _existing_answers(saved, reqs)
    for key, ans in (expected.get("purposeRequirementAnswerMap") or {}).items():
        if saved_answers.get(key) != ans:
            problems.append(f"필수항목 {key} 불일치")
    saved_ids, unresolved = _participant_ids(saved)
    if unresolved:
        problems.append(f"저장된 내부 참석자 {unresolved}명을 확인할 수 없음")
    elif sorted(saved_ids) != sorted(expected.get("participantIdList") or []):
        problems.append("내부 참석자 불일치")
    want_ext = sorted((u["name"], u.get("company") or "") for u in expected.get("externalUserList") or [])
    saved_ext, ext_unknown = _external_users(saved)
    got_ext = sorted((u["name"], u.get("company") or "") for u in saved_ext)
    if ext_unknown:
        problems.append(f"저장된 외부 참석자 {ext_unknown}건의 형태를 해석할 수 없음")
    elif want_ext != got_ext:
        problems.append("외부 참석자 불일치")
    return problems


def cmd_submit(expense_id: str, purpose_id: str, *, memo: str | None = None,
               participants: str | None = None, requirements: str | None = None,
               dry_run: bool = False, external: str | None = None,
               allow_submitted: bool = False, clear_memo: bool = False,
               clear_participants: bool = False, clear_external: bool = False,
               confirm_solo: bool = False) -> None:
    eid = _int_arg(expense_id, "expenseId")
    pid = _int_arg(purpose_id, "purposeId")
    participant_ids = None
    if participants is not None:
        participant_ids = [_int_arg(p, "참석자 userId") for p in participants.split(",") if p.strip()]
    external_users = _parse_external(external) if external is not None else None
    req_map = _parse_requirements(requirements) if requirements else {}

    me = _resolve_me()
    purposes = _active_purposes()
    purpose = purposes.get(pid)
    if purpose is None:
        _err(f"활성 용도 {pid}를 찾을 수 없습니다. purposes로 확인하세요.")
    reqs = purpose.get("requirements") or []
    req_ids = {str(r["id"]) for r in reqs}

    unknown = sorted(set(req_map) - req_ids)
    if unknown:
        _err(f"용도 {pid}에 없는 필수항목 id: {unknown}", validIds=sorted(req_ids))
    if participant_ids:
        member_status = {int(m["userId"]): m.get("status") for m in _members() if m.get("userId") is not None}
        bad = [p for p in participant_ids if member_status.get(p) != "NORMAL"]
        if bad:
            _err("참석자 userId가 재직 사용자 목록에 없습니다.", userIds=bad)

    # 사전 확인: 소유자 → 상태 → 원천 취소/0원
    detail = _owned_detail(eid, me)
    status = detail.get("approvalStatus", "")
    allowed = {"NOT_SUBMITTED", "SUBMITTED"} if allow_submitted else {"NOT_SUBMITTED"}
    if status not in allowed:
        hint = " — 변경하려면 update 커맨드를 쓰세요" if (not allow_submitted and status == "SUBMITTED") else ""
        _out({"skipped": True, "reason": f"Already {status}{hint}", "expenseId": eid})
        return
    void_state = _source_void_state(detail)
    if void_state in ("refund", "voided"):
        _err(f"원천 기록상 취소/0원 이하({void_state}) 건이라 제출을 차단했습니다.", expenseId=eid)
    if void_state == "preauthorized":
        _err("가승인 건이라 제출/변경을 차단했습니다. 최종 매입 확정 후 다시 처리하세요.", expenseId=eid)

    # 생략한 필드는 기존 값을 유지한다 (PUT은 덮어쓰기). 지우려면 --clear-* 를 명시.
    preserved = []
    if memo is None:
        memo_val = "" if clear_memo else (detail.get("memo") or "")
        if memo_val and not clear_memo:
            preserved.append("memo")
    else:
        memo_val = memo
    if participant_ids is None:
        if clear_participants:
            participant_ids = []
        else:
            participant_ids, unresolved = _participant_ids(detail)
            if unresolved:
                _err("기존 내부 참석자를 멤버 목록에서 한 명으로 확인할 수 없어 보존할 수 없습니다. "
                     "--participants로 다시 지정하거나 --clear-participants를 명시하세요.", unresolved=unresolved)
        if participant_ids:
            preserved.append("participants")
    if external_users is None:
        if clear_external:
            external_users = []
        else:
            external_users, ext_unknown = _external_users(detail)
            if ext_unknown:
                _err("기존 외부 참석자 형태를 해석할 수 없어 보존할 수 없습니다. "
                     "--external로 다시 지정하거나 --clear-external을 명시하세요.", unknown=ext_unknown)
        if external_users:
            preserved.append("external")

    catalog = _purpose_catalog()
    old_pid = None
    if detail.get("purpose"):
        old_pid, old_why = _resolve_saved_purpose(detail.get("purpose"), catalog)
        if old_pid is None and _existing_answers(detail) and not requirements:
            _err("기존 용도를 확정할 수 없어 기존 필수항목 답을 안전하게 보존할 수 없습니다. "
                 "--requirements로 답을 다시 지정하세요.", reason=old_why)
    if old_pid is not None and old_pid == pid:
        for k, v in _existing_answers(detail, reqs).items():
            if k in req_ids and k not in req_map:
                req_map[k] = v
                preserved.append(f"requirement:{k}")

    memo_routed = None
    if pid in SERVICE_NAME_PURPOSES and memo is not None and memo_val and reqs:
        service_key = str(reqs[0]["id"])
        if service_key not in req_map:
            req_map[service_key] = [memo_val]
            memo_routed = service_key
            memo_val = detail.get("memo") or ""   # 기존 메모는 유지

    # 자리표시 검사는 기존 답 보존·메모 이동까지 합친 최종 값에 대해 한다(우회 차단).
    placeholders = sorted(k for k, v in req_map.items() if any(x.strip() in PLACEHOLDER_ANSWERS for x in v))
    if placeholders:
        _err("자리표시 값은 필수항목 답으로 쓸 수 없습니다. 실제 내용을 입력하세요.", requirementIds=placeholders)

    missing = [str(r["id"]) for r in reqs if r.get("isRequired") and not req_map.get(str(r["id"]))]
    if missing:
        _err("필수항목이 비어 있습니다. --requirements로 실제 값을 넣으세요.",
             missingRequirementIds=missing,
             requirements=[{"id": r["id"], "item": r.get("item", "")} for r in reqs])

    amount = _amount_krw(detail)
    limit = _num(purpose.get("limitAmount")) or 0.0
    if limit and amount is None and not participant_ids and not external_users:
        _err("원화 금액(krwAmount)이 없어 용도 한도와 비교할 수 없습니다. Gowid에서 원화 확정 금액을 확인한 뒤 처리하세요.",
             currency=detail.get("currency"), limitAmount=limit)
    over_limit = bool(limit) and amount is not None and amount > limit
    if over_limit and not participant_ids and not external_users and not confirm_solo:
        _err("용도 한도를 넘는데 참석자가 없습니다. 함께한 사람을 --participants/--external로 넣거나, "
             "본인 단독이 맞으면 --confirm-solo를 붙이세요.",
             amount=amount, limitAmount=limit,
             note="인당 계산 방식(결제자 포함 여부)은 회사 정책 확인 전이라 자동 판정하지 않습니다.")

    body: dict = {"purposeId": pid}
    if participant_ids:
        body["participantIdList"] = participant_ids
    if external_users:
        body["externalUserList"] = external_users
    if memo_val:
        body["memo"] = memo_val
    if req_map:
        body["purposeRequirementAnswerMap"] = req_map
    # 기존 참석자를 지우는 경우 빈 목록을 명시해 덮어쓴다.
    if clear_participants:
        body["participantIdList"] = []
    if clear_external:
        body["externalUserList"] = []
    if clear_memo:
        body["memo"] = ""

    checks = {
        "owner": "verified (local, not authentication)",
        "previousStatus": status,
        "preservedFromExisting": preserved,
        "memoRoutedToRequirement": memo_routed,
        "amountKrw": amount,
        "overLimit": over_limit,
        "soloConfirmed": bool(confirm_solo and over_limit),
        "sourceState": void_state,
    }
    if dry_run:
        _out({"dry_run": True, "expenseId": eid, "body": body, "checks": checks, "status": "would_submit"})
        return

    put_error = None
    try:
        _request("PUT", f"/v2/expenses/{eid}", body)
    except ApiError as e:
        put_error = str(e)

    # 오류가 났어도 실제 반영됐을 수 있으므로 재조회로 판정한다(같은 요청을 자동 재전송하지 않음).
    saved = _data(f"/v2/expenses/{eid}")
    expected = dict(body)
    expected["memo"] = memo_val
    expected.setdefault("participantIdList", [])
    expected.setdefault("externalUserList", [])
    problems = _postcondition(saved, expected, reqs, catalog)
    result = {
        "success": not problems,
        "expenseId": eid,
        "purposeId": pid,
        "previousStatus": status,
        "status": saved.get("approvalStatus"),
        "purpose": (saved.get("purpose") or {}).get("name"),
        "memo": saved.get("memo"),
        "requirementAnswers": saved.get("purposeRequirementAnswers", []),
        "participants": [u.get("userName") for u in saved.get("participants") or []],
        "external": saved.get("expenseExternalUsers") or [],
        "checks": checks,
    }
    if put_error:
        result["putError"] = put_error
    if problems:
        result["postconditionFailures"] = problems
        _out(result)
        sys.exit(2)
    _out(result)


def cmd_purposes() -> None:
    resp = _data("/v2/purposes?isActivated=true")
    purposes = []
    for p in sorted(resp, key=lambda x: x["name"]):
        reqs = p.get("requirements") or []
        purposes.append({
            "purposeId": p["purposeId"],
            "name": p["name"],
            "category": (p.get("category") or {}).get("name", ""),
            "limitAmount": p.get("limitAmount", 0),
            "hasRequirements": len(reqs) > 0,
            "requirements": [
                {"id": r["id"], "item": r.get("item", ""), "type": r.get("type", "TEXT"),
                 "isRequired": r.get("isRequired", False), "guideDesc": r.get("guideDesc", "")}
                for r in reqs
            ],
        })
    _out(purposes)


def cmd_purpose_requirements(purpose_id: str) -> None:
    pid = _int_arg(purpose_id, "purposeId")
    target = _active_purposes().get(pid)
    if not target:
        _err(f"활성 용도 ID {pid}를 찾을 수 없습니다.")
    result_reqs = []
    for r in target.get("requirements") or []:
        info: dict = {
            "id": r["id"], "item": r.get("item", ""), "type": r.get("type", "TEXT"),
            "isRequired": r.get("isRequired", False), "guideDesc": r.get("guideDesc", ""),
            "isAvailableInput": r.get("isAvailableInput", False),
        }
        if r.get("type") in ("SELECT", "SELECT_MULTI"):
            info["options"] = _api_get(f"/v2/purposes/{pid}/requirements/{r['id']}").get("data", [])
        result_reqs.append(info)
    _out({"purposeId": pid, "purposeName": target["name"], "requirements": result_reqs})


def cmd_members() -> None:
    members = []
    for m in sorted(_data("/v1/members"), key=lambda x: x.get("userName", "")):
        if m.get("status") != "NORMAL":
            continue
        members.append({
            "userId": m["userId"], "userName": m["userName"], "email": m.get("email", ""),
            "department": (m.get("department") or {}).get("name", ""),
        })
    _out(members)


def _load_rules() -> list[dict]:
    rules_file = Path(__file__).resolve().parent.parent / "data" / "auto_rules.json"
    if not rules_file.exists():
        _err("auto_rules.json not found")
    with open(rules_file, encoding="utf-8") as f:
        return json.load(f).get("rules", [])


def cmd_rules(query: str = "") -> None:
    rules = _load_rules()
    if query:
        q = query.lower()
        rules = [r for r in rules if q in (r.get("store_pattern") or "").lower()
                 or q in (r.get("purpose_name") or "").lower()]
    result = [{"pattern": r.get("store_pattern", ""), "purpose": r.get("purpose_name", ""),
               "memo": r.get("requirement_answer", ""), "confidence": r.get("confidence", 0)}
              for r in rules[:50]]
    _out({"count": len(rules), "showing": len(result), "rules": result})


def _pattern_matches(pattern: str, store: str) -> bool:
    """대소문자 무시 포함 매칭. 4자 이하 영숫자 패턴(예: SR)은 단어 경계가 있어야 매칭."""
    p, s = pattern.lower(), store.lower()
    if not p:
        return False
    if len(p) <= 4 and re.fullmatch(r"[a-z0-9]+", p):
        return re.search(rf"(?<![a-z0-9]){re.escape(p)}(?![a-z0-9])", s) is not None
    return p in s


def _command(args: list[str]) -> str:
    return " ".join(shlex.quote(a) for a in args)


def cmd_suggest(expense_id: str) -> None:
    eid = _int_arg(expense_id, "expenseId")
    me = _resolve_me()
    e = _owned_detail(eid, me)
    store = e.get("storeName") or ""
    amount = _amount_krw(e)
    time_str = str(e.get("expenseTime") or "")
    hour = int(time_str[:2]) if time_str[:2].isdigit() else None
    currency = e.get("currency", "KRW")
    purposes = _active_purposes()

    hits = [r for r in _load_rules() if _pattern_matches(r.get("store_pattern") or "", store)]
    # 봇과 같은 방향: 가장 긴(구체적인) 패턴 우선, 그다음 confidence
    hits.sort(key=lambda r: (-len(r.get("store_pattern") or ""), -(r.get("confidence") or 0)))

    matches, inactive = [], []
    for r in hits:
        pid = r.get("purpose_id")
        p = purposes.get(pid)
        if p is None:
            inactive.append({"pattern": r.get("store_pattern"), "purposeId": pid, "purposeName": r.get("purpose_name")})
            continue
        reqs = p.get("requirements") or []
        answer = (r.get("requirement_answer") or "").strip()
        req_map = None
        needs = []
        if reqs:
            if len(reqs) == 1 and answer and answer not in PLACEHOLDER_ANSWERS:
                req_map = {str(reqs[0]["id"]): [answer]}
            else:
                needs = [{"id": q["id"], "item": q.get("item", "")} for q in reqs]
        warnings = []
        if currency == "KRW" and str(p.get("name", "")).startswith(_FOREIGN_ENTITY_PREFIXES):
            warnings.append("원화 결제에 미국법인 용도가 추천되었습니다. 법인을 확인하세요.")
        matches.append({
            "pattern": r.get("store_pattern"), "purposeId": pid, "purposeName": p.get("name"),
            "confidence": r.get("confidence", 0), "requirementAnswerMap": req_map,
            "needsInput": needs, "warnings": warnings,
        })

    meal_candidates = None
    korean_food = currency == "KRW" and any(k in store for k in [
        "쿠팡이츠", "식당", "김밥", "국수", "삼계탕", "닭갈비", "양꼬치", "덮밥", "한식", "카페", "커피", "맥주"])
    top = matches[0] if matches else None
    if (top and top["purposeId"] in MEAL_PURPOSES) or (not matches and korean_food):
        meal_candidates = [
            {"purposeId": pid, "purposeName": purposes[pid]["name"]} for pid in (12556, 12555) if pid in purposes]

    blockers = []
    if meal_candidates is not None:
        blockers.append("식비 시각 기준(점심/야근)은 회사 정책 확인 전이라 자동으로 정하지 않습니다. 사용자에게 어느 용도인지 확인하세요.")
    if top and top["needsInput"]:
        blockers.append("필수항목 실제 값이 필요합니다.")
    if top:
        limit = _num((purposes.get(top["purposeId"]) or {}).get("limitAmount")) or 0.0
        if limit and amount is None:
            blockers.append("원화 금액이 없어 용도 한도와 비교할 수 없습니다. 원화 확정 금액을 확인하세요.")
        elif limit and amount > limit:
            blockers.append("용도 한도를 넘습니다. 함께한 사람을 확인하세요(본인 단독이면 --confirm-solo).")
    void_state = _source_void_state(e)
    if void_state in ("refund", "voided"):
        blockers.append("원천 기록상 취소/0원 이하 건입니다. 제출 대상이 아닙니다.")
    elif void_state == "preauthorized":
        blockers.append("가승인 건입니다. 최종 매입 확정 후 처리하세요.")
    if e.get("approvalStatus") != "NOT_SUBMITTED":
        blockers.append(f"현재 상태가 {e.get('approvalStatus')}입니다. submit 대상이 아닙니다.")

    argv = None
    if top and not blockers:
        argv = ["gowid.py", "submit", str(eid), str(top["purposeId"])]
        if top["requirementAnswerMap"]:
            argv += ["--requirements", json.dumps(top["requirementAnswerMap"], ensure_ascii=False)]

    _out({
        "expenseId": eid, "storeName": store, "amount": amount, "currency": currency,
        "date": e.get("expenseDate", ""), "hour": hour, "status": e.get("approvalStatus", ""),
        "matches": matches[:5], "inactivePurposeMatches": inactive[:5],
        "mealCandidates": meal_candidates, "blockers": blockers,
        "suggestedArgv": argv,
        "suggestedCommand": _command(argv) if argv else None,
    })


_LOCAL_COMMANDS = {"setup", "rules", "help"}


def cmd_setup() -> None:
    email, source = _git_email()
    print("=" * 50)
    print("  Gowid 경비 스킬 셋업 가이드")
    print("=" * 50)
    print()
    print(f"[OK] 본인 이메일: {email} ({source})" if email else
          "[!!] 본인 이메일 미설정 — git config --global user.email \"your@eoeoeo.net\" 또는 GOWID_EMAIL")
    print(f"[{'OK' if API_KEY else '!!'}] GOWID_API_KEY: {'설정됨 (환경변수)' if API_KEY else '미설정'}")
    print()
    if API_KEY and email:
        print("연결 확인 중...")
        try:
            members = _request("GET", "/v1/members")["data"]
        except (ApiError, KeyError, TypeError):
            print("[!!] API 연결 실패 — 키가 올바른지 확인하세요.")
            return
        for m in members:
            if (m.get("email") or "").lower() == email.lower():
                ok = m.get("status") == "NORMAL"
                print(f"[{'OK' if ok else '!!'}] Gowid 사용자 확인: {m.get('userName')} (status={m.get('status')})")
                if ok:
                    print("\n셋업 완료! '내 경비 보여줘'라고 말해보세요.")
                return
        print(f"[!!] {email} 에 매칭되는 Gowid 사용자가 없습니다.")


def _usage() -> None:
    print(__doc__)


def main() -> None:
    args = sys.argv[1:]
    cmd = args[0] if args else "help"

    if cmd not in _LOCAL_COMMANDS and not API_KEY:
        print("API 키 오류. python3 gowid.py setup 을 실행하세요.")
        sys.exit(1)

    if cmd == "setup":
        cmd_setup()
    elif cmd == "whoami":
        cmd_whoami()
    elif cmd == "my-expenses":
        month = ""
        i = 1
        while i < len(args):
            if args[i] == "--all":
                _err("--all(전체 사용자 조회)은 보안상 제거되었습니다. 관리자 조회는 Gowid 관리자 웹을 쓰세요.")
            if args[i] == "--month" and i + 1 < len(args):
                month = args[i + 1]; i += 2
            else:
                _err(f"알 수 없는 옵션: {args[i]}")
        cmd_my_expenses(month=month)
    elif cmd == "detail":
        if len(args) < 2:
            _err("Usage: gowid.py detail <expenseId>")
        cmd_detail(args[1])
    elif cmd in ("submit", "update"):
        if len(args) < 3:
            _err(f"Usage: gowid.py {cmd} <expenseId> <purposeId> [옵션]")
        opts: dict = {}
        value_flags = {"--memo": "memo", "--participants": "participants",
                       "--requirements": "requirements", "--external": "external"}
        bool_flags = {"--dry-run": "dry_run", "--clear-memo": "clear_memo",
                      "--clear-participants": "clear_participants",
                      "--clear-external": "clear_external", "--confirm-solo": "confirm_solo"}
        i = 3
        while i < len(args):
            a = args[i]
            if a in value_flags:
                if i + 1 >= len(args):
                    _err(f"{a} 값이 없습니다.")
                opts[value_flags[a]] = args[i + 1]; i += 2
            elif a in bool_flags:
                opts[bool_flags[a]] = True; i += 1
            else:
                _err(f"알 수 없는 옵션: {a}")
        if opts.get("clear_memo") and "memo" in opts:
            _err("--memo와 --clear-memo는 함께 쓸 수 없습니다.")
        if opts.get("clear_participants") and "participants" in opts:
            _err("--participants와 --clear-participants는 함께 쓸 수 없습니다.")
        if opts.get("clear_external") and "external" in opts:
            _err("--external과 --clear-external은 함께 쓸 수 없습니다.")
        cmd_submit(args[1], args[2], allow_submitted=(cmd == "update"), **opts)
    elif cmd == "suggest":
        if len(args) < 2:
            _err("Usage: gowid.py suggest <expenseId>")
        cmd_suggest(args[1])
    elif cmd == "purposes":
        cmd_purposes()
    elif cmd == "purpose-requirements":
        if len(args) < 2:
            _err("Usage: gowid.py purpose-requirements <purposeId>")
        cmd_purpose_requirements(args[1])
    elif cmd == "members":
        cmd_members()
    elif cmd == "rules":
        cmd_rules(args[1] if len(args) > 1 else "")
    else:
        _usage()


if __name__ == "__main__":
    main()
