"""Isolated regression tests for scripts/gowid.py.

외부 네트워크·실제 키를 쓰지 않는다. 로컬 mock HTTP 서버(127.0.0.1)만 사용하고,
헬퍼는 GOWID_API_BASE를 로컬 주소로만 받는다.
Run: python3 -m unittest discover -s gowid-expense/tests -v
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import threading
import unittest
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "gowid.py"

ME = {"userId": 10, "userName": "Me", "email": "me@example.com", "status": "NORMAL"}
OTHER = {"userId": 11, "userName": "Other User", "email": "other@example.com", "status": "NORMAL"}
SAME_NAME = {"userId": 13, "userName": "Me", "email": "me2@example.com", "status": "NORMAL"}
LEFT = {"userId": 12, "userName": "Left", "email": "left@example.com", "status": "RESIGNED"}

PURPOSES = [
    {"purposeId": 12556, "name": "점심식비", "limitAmount": 12000, "requirements": []},
    {"purposeId": 12555, "name": "야근식비", "limitAmount": 12000, "requirements": []},
    {"purposeId": 12551, "name": "업무교통비", "limitAmount": 0, "requirements": [
        {"id": 126, "item": "출발지", "type": "TEXT", "isRequired": True},
        {"id": 127, "item": "도착지", "type": "TEXT", "isRequired": True}]},
    {"purposeId": 12547, "name": "접대비", "limitAmount": 0, "requirements": [
        {"id": 2052, "item": "소속/이름", "type": "TEXT", "isRequired": True}]},
    {"purposeId": 12532, "name": "IT서비스 이용료", "limitAmount": 0, "requirements": [
        {"id": 360, "item": "서비스,프로그램명 기입", "type": "TEXT", "isRequired": False}]},
    {"purposeId": 97864, "name": "미국법인-보험비", "limitAmount": 0, "requirements": [
        {"id": 900, "item": "어떤 항목인지", "type": "TEXT", "isRequired": True}]},
    {"purposeId": 12531, "name": "서류발급비", "limitAmount": 0, "requirements": [
        {"id": 500, "item": "프로젝트명", "type": "TEXT", "isRequired": True}]},
]


def _clean_env() -> dict:
    """실제 키·이메일·API 주소가 섞이지 않게 GOWID_* 변수를 모두 제거한다."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GOWID_")}


def _u(m):
    return {"userId": m["userId"], "userName": m["userName"], "email": m["email"]}


def _exp(eid, owner, store, krw, *, status="NOT_SUBMITTED", time="123000", date=None, currency="KRW", **kw):
    d = {"expenseId": eid, "storeName": store, "krwAmount": krw, "useAmount": krw, "currency": currency,
         "expenseDate": date or datetime.now().strftime("%Y%m") + "05", "expenseTime": time,
         "approvalStatus": status, "purpose": None, "memo": None, "participants": [],
         "expenseExternalUsers": [], "purposeRequirementAnswers": []}
    if owner is not None:
        d["user"] = _u(owner)
        d["card"] = {"cardNumber": "1234********5678", "cardUser": _u(owner)}
    d.update(kw)
    return d


def base_state():
    month = datetime.now().strftime("%Y%m")
    exps = {
        101: _exp(101, ME, "김밥천국", 30000, time="123000"),
        102: _exp(102, OTHER, "Other Shop", 5000),
        103: _exp(103, SAME_NAME, "Same Name Shop", 7000),
        104: _exp(104, ME, "취소된가게", 0),           # 원천 순액 0원(상세)
        106: _exp(106, ME, "환불가게", 8000),
        107: _exp(107, ME, "비비큐", 80000, status="SUBMITTED",
                  purpose={"purposeId": 12547, "name": "접대비"}, memo="기존메모",
                  participants=[_u(OTHER)], expenseExternalUsers=[{"name": "이한빈", "company": "ABC"}],
                  purposeRequirementAnswers=[{"id": 2052, "item": "소속/이름", "answer": ["ABC 이한빈"]}]),
        108: _exp(108, None, "Ownerless", 1000),
        109: _exp(109, ME, "CLASSROOM CAFE", 5000, time="175900"),
        110: _exp(110, ME, "NEXT INSURANCE", 1000, currency="USD"),
        111: _exp(111, ME, "카카오T일반택시", 15000, time="220000"),
        112: _exp(112, ME, "SR 수서역", 30000),
        113: _exp(113, ME, "NOTION LABS, INC.", 12500),
        114: _exp(114, ME, "DD *DOORDASH", 20000, currency="USD"),
        115: _exp(115, ME, "Apple Store", 9000, status="APPROVED"),
        116: _exp(116, ME, "쿠팡이츠", 9000, time="190000"),
    }
    rows = []
    for eid in (101, 104, 109, 111):
        e = exps[eid]
        r = {k: e[k] for k in ("expenseId", "storeName", "krwAmount", "useAmount", "expenseDate",
                                 "expenseTime", "approvalStatus", "currency")}
        r["cardUserName"] = "Me"
        rows.append(r)
    rows[1]["krwAmount"] = rows[1]["useAmount"] = 20000   # 목록엔 원금액, 상세는 0원
    rows.append({"expenseId": 105, "storeName": "취소된가게", "krwAmount": -20000, "useAmount": -20000,
                 "approvalStatus": "NOT_SUBMITTED", "cardUserName": "Me", "expenseDate": month + "06"})
    rows.append({"expenseId": 106, "storeName": "환불가게", "krwAmount": 8000, "useAmount": 8000, "isRefund": True,
                 "approvalStatus": "NOT_SUBMITTED", "cardUserName": "Me", "expenseDate": month + "06"})
    rows.append({"expenseId": 102, "storeName": "Other Shop", "krwAmount": 5000, "useAmount": 5000,
                 "approvalStatus": "NOT_SUBMITTED", "cardUserName": "Other User", "expenseDate": month + "06"})
    rows.append({"expenseId": 103, "storeName": "Same Name Shop", "krwAmount": 7000, "useAmount": 7000,
                 "approvalStatus": "NOT_SUBMITTED", "cardUserName": "Me", "expenseDate": month + "06"})
    rows.append({"expenseId": 199, "storeName": "Unnamed card", "krwAmount": 7000, "useAmount": 7000,
                 "approvalStatus": "NOT_SUBMITTED", "cardUserName": "", "expenseDate": month + "06"})
    rows.append({"expenseId": 198, "storeName": "Next month", "krwAmount": 7000, "useAmount": 7000,
                 "approvalStatus": "NOT_SUBMITTED", "cardUserName": "Me", "expenseDate": "29991201"})
    for i in range(240):   # 3페이지 이상이 되도록 타인 거래로 채움
        rows.append({"expenseId": 5000 + i, "storeName": f"F{i}", "krwAmount": 100, "useAmount": 100,
                     "approvalStatus": "NOT_SUBMITTED", "cardUserName": "Other User", "expenseDate": month + "02"})
    # 마지막 페이지에 본인 건 하나 (페이지 잘림 회귀 확인용)
    exps[120] = _exp(120, ME, "LastPageShop", 3000)
    rows.append({"expenseId": 120, "storeName": "LastPageShop", "krwAmount": 3000, "useAmount": 3000,
                 "approvalStatus": "NOT_SUBMITTED", "cardUserName": "Me", "expenseDate": month + "01"})
    return {"members": [ME, OTHER, SAME_NAME, LEFT], "purposes": PURPOSES, "expenses": exps,
            "rows": rows, "put_mode": "apply", "log": []}


class Handler(BaseHTTPRequestHandler):
    state: dict = {}

    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        st = self.state
        u = urlparse(self.path)
        q = parse_qs(u.query)
        st["log"].append(("GET", self.path, None))
        if self.headers.get("Authorization") != "dummy-test-key":
            return self._send({}, 401)
        p = u.path
        if p == "/v1/members":
            return self._send({"data": st["members"]})
        if p == "/v2/purposes":
            return self._send({"data": st["purposes"]})
        if p == "/v2/expense-statements":
            page, size = int(q["page"][0]), int(q["size"][0])
            rows = st["rows"]
            total_pages = (len(rows) + size - 1) // size
            chunk = rows[page * size:(page + 1) * size]
            return self._send({"data": {"content": chunk, "totalPages": total_pages,
                                        "last": page >= total_pages - 1}})
        if p.startswith("/v2/expenses/") or p.startswith("/v1/expenses/"):
            e = st["expenses"].get(int(p.rsplit("/", 1)[1]))
            return self._send({"data": e}) if e else self._send({}, 404)
        self._send({}, 404)

    def do_PUT(self):
        st = self.state
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode())
        st["log"].append(("PUT", self.path, body))
        eid = int(self.path.rsplit("/", 1)[1])
        e = st["expenses"][eid]
        mode = st["put_mode"]
        if mode == "error_no_apply":
            return self._send({}, 500)
        if mode != "noop":
            # 최악의 덮어쓰기 모델: body에 없는 필드는 지워진다.
            pid = body["purposeId"]
            name = next(p["name"] for p in st["purposes"] if p["purposeId"] == pid)
            e["purpose"] = {"purposeId": pid, "name": name}
            e["approvalStatus"] = "SUBMITTED"
            e["memo"] = body.get("memo")
            ids = body.get("participantIdList") or []
            e["participants"] = [_u(m) for m in st["members"] if m["userId"] in ids]
            e["expenseExternalUsers"] = body.get("externalUserList") or []
            answers = body.get("purposeRequirementAnswerMap") or {}
            if mode == "drop_answers":
                answers = {}
            e["purposeRequirementAnswers"] = [{"id": int(k), "item": "", "answer": v} for k, v in answers.items()]
        if mode == "error_after_apply":
            return self._send({}, 500)
        self._send({"data": None})


class GowidCliTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        Handler.state = base_state()

    @property
    def st(self):
        return Handler.state

    def run_cli(self, *args, email="me@example.com", base=None, key="dummy-test-key"):
        env = _clean_env()
        env.update({"GOWID_API_KEY": key, "GOWID_EMAIL": email,
               "GOWID_API_BASE": base or f"http://127.0.0.1:{self.port}", "GOWID_HTTP_TIMEOUT": "5",
               "PYTHONDONTWRITEBYTECODE": "1"})
        p = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env, timeout=60)
        try:
            out = json.loads(p.stdout) if p.stdout.strip().startswith(("{", "[")) else None
        except json.JSONDecodeError:
            out = None
        return p.returncode, out, p.stdout + p.stderr

    def puts(self):
        return [x for x in self.st["log"] if x[0] == "PUT"]

    # ── P0: 본인 식별 / 소유자 ──
    def test_submit_other_users_expense_blocked(self):
        rc, out, _ = self.run_cli("submit", "102", "12556")
        self.assertEqual(rc, 1)
        self.assertIn("본인 경비가 아닙니다", out["error"])
        self.assertEqual(self.puts(), [])

    def test_detail_and_suggest_other_users_blocked(self):
        for cmd in ("detail", "suggest"):
            rc, out, _ = self.run_cli(cmd, "102")
            self.assertEqual(rc, 1, cmd)
            self.assertIn("본인 경비가 아닙니다", out["error"])

    def test_update_other_users_blocked(self):
        rc, out, _ = self.run_cli("update", "103", "12556")
        self.assertEqual(rc, 1)
        self.assertEqual(self.puts(), [])

    def test_ownerless_expense_fails_closed(self):
        rc, out, _ = self.run_cli("detail", "108")
        self.assertEqual(rc, 1)
        self.assertIn("소유자를 확인할 수 없어", out["error"])

    def test_resigned_member_rejected(self):
        rc, out, _ = self.run_cli("whoami", email="left@example.com")
        self.assertEqual(rc, 1)
        self.assertIn("NORMAL", out["error"])

    def test_duplicate_email_rejected(self):
        self.st["members"].append(dict(ME, userId=99))
        rc, out, _ = self.run_cli("whoami")
        self.assertEqual(rc, 1)
        self.assertIn("여러 명", out["error"])

    def test_whoami_reports_not_authentication(self):
        rc, out, _ = self.run_cli("whoami")
        self.assertEqual(rc, 0)
        self.assertEqual(out["userId"], 10)
        self.assertEqual(out["identitySource"], "GOWID_EMAIL")
        self.assertIn("인증이 아닙니다", out["note"])

    def test_all_flag_removed(self):
        rc, out, _ = self.run_cli("my-expenses", "--all")
        self.assertEqual(rc, 1)
        self.assertIn("제거", out["error"])
        self.assertFalse(any("expense-statements" in x[1] for x in self.st["log"]))

    def test_api_base_override_local_only(self):
        rc, out, _ = self.run_cli("whoami", base="https://evil.example.com")
        self.assertEqual(rc, 1)
        self.assertIn("로컬 주소", out["error"])

    def test_participant_must_be_active_member(self):
        rc, out, _ = self.run_cli("submit", "101", "12556", "--participants", "12")
        self.assertEqual(rc, 1)
        self.assertEqual(self.puts(), [])

    # ── my-expenses: 페이지/월/취소/소유자 ──
    def test_my_expenses_full_pagination_and_filters(self):
        rc, out, _ = self.run_cli("my-expenses")
        self.assertEqual(rc, 0, out)
        ids = sorted(e["expenseId"] for e in out["expenses"])
        self.assertEqual(ids, [101, 109, 111, 120])   # 120은 마지막 페이지
        ex = out["excluded"]
        self.assertEqual(ex["voidByDetail"], 1)              # 104 상세 순액 0
        self.assertEqual(ex["sourceVoidOrRefundRows"], 2)    # 105 음수행, 106 isRefund
        self.assertEqual(ex["ownerMismatchSameName"], 1)     # 103 동명이인
        self.assertEqual(ex["unnamedCardRows"], 1)
        self.assertEqual(ex["outOfMonthRows"], 1)
        pages = [x for x in self.st["log"] if "expense-statements" in x[1]]
        self.assertEqual(len(pages), 3)

    def test_no_amount_pairing_inference(self):
        # 같은 가게·같은 금액 ± 행이 있어도 원거래를 짝지어 지우지 않는다(원천 필드만 사용).
        month = datetime.now().strftime("%Y%m")
        self.st["expenses"][130] = _exp(130, ME, "PairShop", 9000)
        self.st["rows"][:0] = [
            {"expenseId": 130, "storeName": "PairShop", "krwAmount": 9000, "useAmount": 9000,
             "approvalStatus": "NOT_SUBMITTED", "cardUserName": "Me", "expenseDate": month + "07"},
            {"expenseId": 131, "storeName": "PairShop", "krwAmount": -9000, "useAmount": -9000,
             "approvalStatus": "NOT_SUBMITTED", "cardUserName": "Me", "expenseDate": month + "08"}]
        rc, out, _ = self.run_cli("my-expenses")
        self.assertIn(130, [e["expenseId"] for e in out["expenses"]])

    def test_month_range_inclusive_last_day(self):
        self.run_cli("my-expenses", "--month", "2026-02")
        q = next(x[1] for x in self.st["log"] if "expense-statements" in x[1])
        self.assertIn("startDate=20260201", q)
        self.assertIn("endDate=20260228", q)

    def test_invalid_month_rejected(self):
        for bad in ("2026-3", "202613", "abc"):
            rc, out, _ = self.run_cli("my-expenses", "--month", bad)
            self.assertEqual(rc, 1, bad)
            self.assertIn("형식", out["error"])
        self.assertFalse(any("expense-statements" in x[1] for x in self.st["log"]))

    # ── submit: 입력 검증 / 필수항목 / 메모 ──
    def test_invalid_ids_no_traceback(self):
        for args in (("submit", "101", "abc"), ("submit", "x", "12556"), ("submit", "101", "12556", "--participants", "a")):
            rc, out, raw = self.run_cli(*args)
            self.assertEqual(rc, 1, args)
            self.assertNotIn("Traceback", raw)

    def test_memo_not_swallowed_for_non_service_purpose(self):
        rc, out, _ = self.run_cli("submit", "111", "12551", "--memo", "출장", "--dry-run")
        self.assertEqual(rc, 1)
        self.assertEqual(out["missingRequirementIds"], ["126", "127"])

    def test_memo_preserved_with_requirements(self):
        rc, out, _ = self.run_cli("submit", "111", "12551", "--memo", "고객 미팅",
                                  "--requirements", '{"126":["강남역"],"127":["판교역"]}')
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["memo"], "고객 미팅")

    def test_service_memo_routed_only_for_service_purposes(self):
        rc, out, _ = self.run_cli("submit", "113", "12532", "--memo", "Notion 워크스페이스", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertEqual(out["body"]["purposeRequirementAnswerMap"], {"360": ["Notion 워크스페이스"]})
        self.assertNotIn("memo", out["body"])

    def test_placeholder_answer_blocked(self):
        rc, out, _ = self.run_cli("submit", "111", "12551", "--requirements", '{"126":["업무 이동"],"127":["판교"]}')
        self.assertEqual(rc, 1)
        self.assertIn("자리표시", out["error"])
        self.assertEqual(self.puts(), [])

    def test_unknown_requirement_id_blocked(self):
        rc, out, _ = self.run_cli("submit", "111", "12551", "--requirements", '{"999":["x"]}')
        self.assertEqual(rc, 1)

    def test_inactive_purpose_rejected(self):
        rc, out, _ = self.run_cli("submit", "101", "94177")
        self.assertEqual(rc, 1)
        self.assertIn("활성 용도", out["error"])

    # ── 한도/참석자 ──
    def test_over_limit_without_participants_blocked(self):
        rc, out, _ = self.run_cli("submit", "101", "12556")
        self.assertEqual(rc, 1)
        self.assertIn("참석자", out["error"])
        self.assertEqual(self.puts(), [])

    def test_over_limit_with_participants_or_confirm_solo(self):
        rc, out, _ = self.run_cli("submit", "101", "12556", "--participants", "11", "--dry-run")
        self.assertEqual(rc, 0)
        rc, out, _ = self.run_cli("submit", "101", "12556", "--confirm-solo", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertTrue(out["checks"]["soloConfirmed"])

    # ── 원천 취소 ──
    def test_source_voided_expense_blocked(self):
        rc, out, _ = self.run_cli("submit", "104", "12556")
        self.assertEqual(rc, 1)
        self.assertIn("취소", out["error"])
        self.assertEqual(self.puts(), [])

    # ── postcondition ──
    def test_postcondition_success(self):
        rc, out, _ = self.run_cli("submit", "109", "12556")
        self.assertEqual(rc, 0, out)
        self.assertTrue(out["success"])
        self.assertEqual(out["status"], "SUBMITTED")

    def test_postcondition_noop_reports_failure(self):
        self.st["put_mode"] = "noop"
        rc, out, _ = self.run_cli("submit", "109", "12556")
        self.assertEqual(rc, 2)
        self.assertFalse(out["success"])
        self.assertTrue(any("status" in p for p in out["postconditionFailures"]))

    def test_postcondition_dropped_answers_detected(self):
        self.st["put_mode"] = "drop_answers"
        rc, out, _ = self.run_cli("submit", "111", "12551", "--requirements", '{"126":["강남"],"127":["판교"]}')
        self.assertEqual(rc, 2)
        self.assertTrue(any("필수항목" in p for p in out["postconditionFailures"]))

    def test_put_error_but_applied_is_verified_by_readback(self):
        self.st["put_mode"] = "error_after_apply"
        rc, out, _ = self.run_cli("submit", "109", "12556")
        self.assertEqual(rc, 0, out)
        self.assertTrue(out["success"])
        self.assertIn("putError", out)
        self.assertEqual(len(self.puts()), 1)   # 자동 재전송 없음

    def test_put_error_not_applied_fails(self):
        self.st["put_mode"] = "error_no_apply"
        rc, out, _ = self.run_cli("submit", "109", "12556")
        self.assertEqual(rc, 2)
        self.assertEqual(len(self.puts()), 1)

    def test_duplicate_submit_skipped(self):
        rc, out, _ = self.run_cli("submit", "107", "12547")
        self.assertEqual(rc, 0)
        self.assertTrue(out["skipped"])
        self.assertEqual(self.puts(), [])

    def test_approved_not_updatable(self):
        rc, out, _ = self.run_cli("update", "115", "12532")
        self.assertTrue(out["skipped"])
        self.assertEqual(self.puts(), [])

    # ── update: 생략 필드 보존 ──
    def test_update_preserves_omitted_fields(self):
        rc, out, _ = self.run_cli("update", "107", "12547")
        self.assertEqual(rc, 0, out)
        body = self.puts()[0][2]
        self.assertEqual(body["participantIdList"], [11])
        self.assertEqual(body["externalUserList"], [{"name": "이한빈", "company": "ABC"}])
        self.assertEqual(body["memo"], "기존메모")
        self.assertEqual(body["purposeRequirementAnswerMap"], {"2052": ["ABC 이한빈"]})
        self.assertTrue(out["success"])

    def test_update_preserves_answers_matched_by_item_name(self):
        # 응답 answer의 id가 요구항목 id가 아니어도 항목명으로 보존·검증한다.
        self.st["expenses"][107]["purposeRequirementAnswers"] = [{"id": 77777, "item": "소속/이름", "answer": ["ABC 이한빈"]}]
        rc, out, _ = self.run_cli("update", "107", "12547", "--dry-run")
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["body"]["purposeRequirementAnswerMap"], {"2052": ["ABC 이한빈"]})

    def test_service_memo_routing_keeps_existing_memo(self):
        self.st["expenses"][113]["memo"] = "기존 설명"
        rc, out, _ = self.run_cli("submit", "113", "12532", "--memo", "Notion 워크스페이스", "--dry-run")
        self.assertEqual(out["body"]["memo"], "기존 설명")

    def test_update_purpose_change_requires_new_requirements(self):
        rc, out, _ = self.run_cli("update", "107", "12531")
        self.assertEqual(rc, 1)
        self.assertEqual(out["missingRequirementIds"], ["500"])
        self.assertEqual(self.puts(), [])

    def test_update_explicit_clear(self):
        rc, out, _ = self.run_cli("update", "107", "12547", "--clear-participants", "--clear-external",
                                  "--clear-memo", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertEqual(out["body"]["participantIdList"], [])
        self.assertEqual(out["body"]["externalUserList"], [])
        self.assertEqual(out["body"]["memo"], "")

    def test_conflicting_clear_flags(self):
        rc, out, _ = self.run_cli("update", "107", "12547", "--memo", "a", "--clear-memo")
        self.assertEqual(rc, 1)

    # ── suggest ──
    def test_suggest_short_pattern_boundary(self):
        rc, out, _ = self.run_cli("suggest", "109")   # CLASSROOM CAFE ≠ SR
        self.assertNotIn("SR", [m["pattern"] for m in out["matches"]])
        rc, out, _ = self.run_cli("suggest", "112")   # 'SR 수서역'
        self.assertIn("SR", [m["pattern"] for m in out["matches"]])

    def test_suggest_shell_quoting(self):
        rc, out, _ = self.run_cli("suggest", "110")
        self.assertEqual(rc, 0, out)
        import shlex
        self.assertEqual(shlex.split(out["suggestedCommand"]), out["suggestedArgv"])
        self.assertIn("Worker's Comp", out["suggestedArgv"][-1])
        # 실제 셸로 해석해도 인자가 그대로 보존되는지(실행은 printf만)
        cmd = "printf '%s\\n' " + out["suggestedCommand"].split(" ", 1)[1]
        p = subprocess.run(["/bin/bash", "-c", cmd], capture_output=True, text=True)
        self.assertEqual(p.stdout.splitlines(), out["suggestedArgv"][1:])

    def test_suggest_placeholder_not_autofilled(self):
        rc, out, _ = self.run_cli("suggest", "111")
        top = out["matches"][0]
        self.assertIsNone(top["requirementAnswerMap"])
        self.assertEqual([r["id"] for r in top["needsInput"]], [126, 127])
        self.assertIsNone(out["suggestedCommand"])

    def test_suggest_meal_time_not_decided(self):
        for eid in ("116", "101"):
            rc, out, _ = self.run_cli("suggest", eid)
            self.assertIsNone(out["suggestedCommand"], eid)
            self.assertEqual([c["purposeId"] for c in out["mealCandidates"]], [12556, 12555])

    def test_suggest_inactive_purpose_excluded(self):
        rc, out, _ = self.run_cli("suggest", "114")
        self.assertEqual(out["matches"], [])
        self.assertEqual(out["inactivePurposeMatches"][0]["purposeId"], 94177)

    def test_suggest_service_answer_and_longest_pattern(self):
        rc, out, _ = self.run_cli("suggest", "113")
        top = out["matches"][0]
        self.assertEqual(top["purposeId"], 12532)
        self.assertEqual(top["requirementAnswerMap"], {"360": ["Notion 워크스페이스"]})
        self.assertIsNotNone(out["suggestedCommand"])

    def test_suggest_never_writes(self):
        for eid in ("109", "110", "111", "113"):
            self.run_cli("suggest", eid)
        self.assertEqual(self.puts(), [])

    # ── 로컬 명령 ──
    def test_rules_works_without_key(self):
        env = _clean_env()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p = subprocess.run([sys.executable, str(SCRIPT), "rules", "notion"], capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0)
        self.assertGreaterEqual(json.loads(p.stdout)["count"], 1)


if __name__ == "__main__":
    unittest.main()
