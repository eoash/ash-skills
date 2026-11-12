---
name: gowid-expense
description: Gowid 법인카드 경비 관리 어시스턴트. 미제출 경비 조회, 용도 지정, 제출, 자동 분류 규칙 확인. "경비", "미제출", "고위드", "gowid" 요청에 사용.
triggers:
  - "경비"
  - "미제출"
  - "내 경비"
  - "경비 제출"
  - "고위드"
  - "gowid"
---

# Gowid 경비 어시스턴트

Gowid 법인카드 미제출 경비를 조회하고, 용도를 지정하여 제출하는 Claude Code / Codex 공용 스킬.

## 셋업 확인

스킬 실행 시 **반드시 먼저** 아래를 확인:

```bash
# Claude Code 설치 경로
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py whoami

# Codex에 설치한 경우 (설치돼 있을 때만)
python3 ~/.codex/skills/gowid-expense/scripts/gowid.py whoami

# Windows 사용자는 python3 대신 python 사용
```

API 키는 스크립트에 내장되어 있지 않다. 환경변수 `GOWID_API_KEY`가 필요하다.

- `API 키 오류` / `401 API 키가 만료되었거나 잘못되었습니다` → 키 미설정 또는 회전된 옛 키. 로컬 `.env` 사본은 옛 키일 수 있으니 맥미니 고위드 봇(`com.eo.gowid-bot`)이 쓰는 현행 키를 운영팀에 받는다
- 권장 저장: `~/.gowid-api-key`(chmod 600) + `.zshrc`에 `[ -f ~/.gowid-api-key ] && export GOWID_API_KEY="$(cat ~/.gowid-api-key)"`. 키를 채팅·명령줄에 붙여넣지 않는다

## 사용자 식별과 보안 한계

```bash
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py whoami
```

- 본인 이메일은 `GOWID_EMAIL`(있으면 우선) 또는 `git config user.email`에서 읽고, Gowid 멤버 목록에서 **재직(NORMAL) 상태이고 이메일이 정확히 한 명과 일치**할 때만 본인으로 인정한다.
- `detail`·`suggest`·`submit`·`update`는 경비 상세의 소유자 userId가 본인 userId와 같을 때만 진행한다. 소유자를 확인할 수 없으면 차단한다. `my-expenses`도 이름이 아니라 상세의 소유자 ID로 최종 확인한다.
- 전체 사용자 조회(`--all`)는 제거했다.
- **이것은 인증이 아니다.** API 키는 회사 공용이고, 이메일 설정은 로컬에서 바꿀 수 있다. 이 헬퍼를 정상 사용하는 사람이 실수로 남의 경비를 다루는 것은 막지만, 키를 가진 사람이 다른 사람 이메일을 설정하거나 API를 직접 호출하는 것은 막지 못한다. 진짜 본인 제한에는 서버측 인증 중계나 사용자별 자격증명이 필요하다.

## 헬퍼 스크립트

모든 API 호출은 `scripts/gowid.py`를 통해 수행. 설치 경로 예시:

```
~/.codex/skills/gowid-expense/scripts/gowid.py
~/.claude/skills/gowid-expense/scripts/gowid.py
```

## 워크플로우

### 1. 내 미제출 경비 조회

사용자가 "내 경비", "미제출", "경비 보여줘" 등 요청 시:

```bash
# 기본: 이번 달 본인 경비
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py my-expenses

# 지난달 / 특정 월 조회 — 사용자가 "3월 경비", "지난달 미제출" 등 요청 시 (YYYYMM 또는 YYYY-MM)
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py my-expenses --month 202603
```

- 해당 월(1일~말일)의 모든 페이지를 끝까지 읽는다. 안전 상한에 걸리면 잘린 결과를 내지 않고 오류로 멈춘다.
- 취소·환불은 **원천 레코드 자체의 값으로만** 제외한다: 음수/0원 행, `isRefund=true` 행, 상세 순액이 0원 이하가 된 건. 같은 가맹점·같은 금액의 ± 행을 짝지어 지우는 추정은 하지 않는다.
- `excluded`에 제외 사유별 건수가 나온다. 카드 사용자명이 비어 있는 미제출 건은 본인 여부를 확정할 수 없어 표시하지 않고 건수만 알린다.

결과를 **한국어 테이블**로 표시:

```
📋 미제출 경비 (N건)

| # | 날짜 | 가맹점 | 금액 | 추천 용도 | ID |
|---|------|--------|------|----------|-----|
| 1 | 03/26 | READ - MEETING ... | 30,430원 | IT서비스 이용료 | 32625805 |
```

- 금액이 USD/SGP 등 해외인 경우 원화 환산 금액도 함께 표시
- 용도 추천은 auto_rules 기반 (헬퍼가 처리)
- `--month` 미지정 시 이번 달만 반환 — "지난달 경비 안 보여요" 문의는 대부분 월 파라미터 누락

### 2. 경비 자동 분류 추천 (suggest)

사용자가 "이거 뭐로 제출해야 해?", "32625805 추천해줘", "규칙 추천" 등 요청 시:

```bash
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py suggest <expenseId>
```

내부 동작:
1. 본인 경비인지 확인한 뒤 상세(`storeName`, `krwAmount`, `expenseTime`) 조회
2. `data/auto_rules.json`의 341개 패턴과 매칭. **가장 긴 패턴 우선**, 같으면 confidence 순. 4자 이하 영숫자 패턴(예: `SR`)은 단어 경계가 있어야 매칭
3. 비활성 용도로 가는 규칙은 `inactivePurposeMatches`로 따로 보여주고 추천하지 않는다
4. **식비(점심/야근)는 시각으로 자동 결정하지 않는다.** 회사 기준 시각이 확인되지 않았다(스킬 18시, 봇 17시, 옛 README 19시로 서로 달랐음). `mealCandidates`를 보여주고 사용자에게 고르게 한다
5. 필수항목이 1개이고 규칙 답이 실제 값일 때만 자동으로 채운다. 자리표시 답(`업무 이동`, `출장`, `IT서비스 정기결제`, `식비`, `소모품`)이나 필수항목이 여러 개인 용도는 `needsInput`으로 넘긴다
6. 막히는 이유가 없을 때만 `suggestedCommand`(셸 인용 처리됨)와 `suggestedArgv`를 준다. 이유는 `blockers`에 나온다

출력 예:

```json
{
  "storeName": "NOTION.SO",
  "amount": 12500,
  "matches": [
    {"purposeName": "IT서비스 이용료", "purposeId": 12532, "confidence": 1.0, "requirementAnswerMap": {"360": ["Notion 워크스페이스"]}}
  ],
  "suggestedCommand": "gowid.py submit 32625805 12532 --requirements '{\"360\": [\"Notion 워크스페이스\"]}'"
}
```

사용자에게는 top 매칭 1건을 한국어로 요약해서 보여주고, `blockers`가 비어 있고 사용자가 동의하면 `suggestedCommand`를 실행한다. `blockers`가 있으면 그 내용을 사용자에게 묻는다:

```
💡 NOTION.SO 12,500원 → IT서비스 이용료 (confidence 1.0)
   서비스명: Notion 워크스페이스

제출할까요? [y/N]
```

**언제 유용한가**:
- 규칙이 있는 가맹점(Anthropic, GitHub, Vercel, AWS, Slack 등) → 용도·서비스명 추천
- 한국 식당 → 점심/야근 후보만 제시 (사용자가 선택)
- 필수항목 있는 용도(업무교통비, 도서구입비 등) → 실제 값을 사용자에게 묻는다

### 3. 경비 제출

사용자가 "이거 식비로 제출해", "32625805 IT서비스로 제출" 등 요청 시:

```bash
# 용도 지정 + 제출 (먼저 --dry-run으로 보낼 내용 확인)
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py submit <expenseId> <purposeId> [--memo "메모"] [--participants "id1,id2"] [--dry-run]
```

제출 전에 헬퍼가 확인하는 것: 본인 경비, 활성 용도, 필수항목 id가 그 용도에 있는지, 필수 답이 모두 있는지, 자리표시 답이 아닌지, 참석자가 재직자인지, 원천 기록상 취소/0원 이하가 아닌지. 하나라도 어긋나면 서버에 쓰지 않고 멈춘다.

**식비 제출 시**:
- 결제 금액이 용도의 `limitAmount`(Gowid 설정값)를 넘는데 참석자가 없으면 차단한다. "누구랑 먹었어요?"라고 묻고 `--participants`/`--external`을 넣는다. 본인 단독이 맞으면 `--confirm-solo`를 붙인다
- 인당 금액 계산 방식(결제자를 인원에 넣는지)은 회사 정책 확인 전이라 헬퍼가 판정하지 않는다
- 참석자 이름 → userId 변환은 `gowid.py members`로 조회 (재직자만 나온다)

**접대비 제출 시 (외부 참석자)**:
- 내부 참석자는 `--participants "userId,userId"`, 외부 참석자는 `--external "이름:소속,이름"`(소속 생략 가능)
- 필수항목 `소속/이름`(2052)에 상대방 소속/이름을 함께 기입

```bash
python3 gowid.py submit <expenseId> 12547 --participants "2196,2911" \
  --external "이한빈:ABC,이윤섭" --requirements '{"2052": ["ABC 이한빈, 이윤섭"]}'
```

**IT서비스 제출 시**:
- `서비스,프로그램명 기입` 필드(`purposeRequirementAnswerMap["360"]`)에 서비스명 자동 기입 (예: "Notion 워크스페이스")
- IT서비스·멤버십·매거진(12532/70602/12536)에서만, 서비스명 칸이 비어 있으면 `--memo` 값을 그 칸으로 옮긴다. 다른 용도에서는 메모를 메모로 그대로 둔다

### 3-1. 이미 제출된 건 수정 (update)

사용자가 "이거 서류발급비로 바꿔", "제출한 거 용도 변경" 등 요청 시. **SUBMITTED(승인 대기) 상태는 API로 용도·필수항목·참석자·메모를 바꿀 수 있다** (2026-11-09 실증, `PUT /v2/expenses/{id}`).

```bash
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py update <expenseId> <purposeId> [submit과 같은 옵션]
```

- `submit`은 미제출(NOT_SUBMITTED)만 처리하고 SUBMITTED는 건너뛴다 → 변경은 `update`로
- `update`는 NOT_SUBMITTED·SUBMITTED만 허용. APPROVED 등 승인 이후 상태는 API 변경을 검증하지 않았으므로 Gowid 웹 안내
- 지정하지 않은 메모·참석자·외부 참석자는 기존 값을 다시 보내 유지한다. 용도가 같으면 기존 필수항목 답도 유지한다. 지우려면 `--clear-memo`, `--clear-participants`, `--clear-external`을 명시한다
- 용도를 바꾸면 새 용도의 필수항목을 `--requirements`로 넣어야 한다 (비어 있으면 차단)
- submit/update 모두 저장 후 다시 조회해 status=SUBMITTED, 용도, 메모, 필수항목, 내부·외부 참석자가 요청과 같은지 검사한다. 하나라도 다르면 `success:false`, `postconditionFailures`, 종료코드 2로 끝난다. 쓰기 요청이 오류를 내도 재조회로 실제 반영 여부를 판정하며, 같은 요청을 자동으로 다시 보내지 않는다
- 제출 취소(미제출로 되돌리기) API는 없다 → Gowid 웹

### 4. 용도 목록 조회

```bash
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py purposes
```

### 5. 팀원 목록 (참석자 선택용)

```bash
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py members
```

### 6. 경비 상세 조회

```bash
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py detail <expenseId>
```

### 7. 자동 분류 규칙 조회

```bash
python3 ~/.claude/skills/gowid-expense/scripts/gowid.py rules [검색어]
```

### 8. 규칙 추가 제안

사용자가 "이 가맹점 규칙 추가해줘" 요청 시:
1. 가맹점 패턴, 용도, 메모를 확인
2. GitHub Issue 생성 제안:

```bash
gh issue create --repo EO-Studio-Dev/gowid-expense-bot \
  --title "규칙 추가: <가맹점> → <용도>" \
  --body "패턴: <pattern>\n용도: <purposeName> (ID: <purposeId>)\n메모: <memo>\n제안자: $(git config user.email)"
```

## 용도 ID 빠른 참조

| ID | 용도 | API 제출 | 비고 |
|----|------|---------|------|
| 12556 | 점심식비 | ✅ 가능 | 인당 12,000원 |
| 12555 | 야근식비 | ✅ 가능 | 인당 12,000원 |
| 131887 | 금요미식회(점심식비) | ✅ 가능 | 인당 15,000원 |
| 12553 | 회식비 | ✅ 가능 | |
| 12552 | 기타식비 | ✅ 가능 | |
| 12532 | IT서비스 이용료 | ✅ 가능 | `서비스,프로그램명 기입`에 서비스명 |
| 70602 | 멤버십 구독료 | ✅ 가능 | 서비스명/구독명을 필수항목에 기입 |
| 12536 | 매거진 구독료 | ✅ 가능 | 매체명/구독명을 필수항목에 기입 |
| 12546 | 우편비 | ✅ 가능 | |
| 72341 | 통신비 | ✅ 가능 | |
| 72017 | 노트북 대여(정기결제) | ✅ 가능 | |
| 12533 | 소모품비(10만원이하) | ✅ 가능 | |
| 12551 | 업무교통비 | ✅ 가능 | 필수항목: 출발지/도착지 (`--requirements`) |
| 12550 | 야근교통비 | ✅ 가능 | 필수항목: 출퇴근 시간 (`--requirements`) |
| 12537 | 도서구입비 | ✅ 가능 | 필수항목: 책 제목 (`--requirements`) |
| 12531 | 서류발급비 | ✅ 가능 | 필수항목: 프로젝트명 (`--requirements`) |
| 85747 | 업무추진비(스탭식비,촬영음료) | ✅ 가능 | 프로젝트 필요 |
| 12547 | 접대비 | ✅ 가능 | 필수 `소속/이름`(2052), 외부 참석자 `--external` |
| 28453 | 주차비 | ✅ 가능 | 필수 `프로젝트명`(3116) |
| 166171 | 법인차량렌트비 | ✅ 가능 | 필수항목 없음 |
| 21396 | 장비 구매(10만원이상) | ✅ 가능 | 필수 `어떤 품목`(2164) |
| 12541 | 보험비 | ✅ 가능 | 필수 `사무실보험,화재보험등`(3118). 서울보증 보증보험료는 서류발급비로 처리(운영 기준) |
| 12527 | 기타비용 | ✅ 가능 | 필수 `왜 기타항목인지`(835) |
| 94176 | 미국법인-지급수수료 | ✅ 가능 | 필수 `어떤 항목인지`(2161) |
| 12530 | 온라인 마케팅 | ✅ 가능 | 프로젝트 필요 |

필수항목 id·한도는 바뀔 수 있으니 제출 전 `purposes`로 확인한다.

## 필수항목(Requirements) 있는 용도 제출

일부 용도는 필수 입력항목이 있다 (예: 업무교통비 → 출발지/도착지, 도서구입비 → 책 제목).
모든 필수항목은 현재 TEXT 타입이며, `purposeRequirementAnswerMap`으로 API 제출 가능.

**제출 워크플로우:**
1. `purposes` 커맨드에서 `hasRequirements: true`인 용도의 `requirements` 배열 확인
2. 필수항목이 SELECT/SELECT_MULTI 타입이면 `purpose-requirements <purposeId>`로 선택지 조회
3. 사용자에게 필수항목 값 확인 후, `--requirements` 플래그로 제출

```
# 필수항목 상세 조회
python3 gowid.py purpose-requirements 12551

# 필수항목 포함 제출
python3 gowid.py submit <expenseId> 12551 --requirements '{"126": ["서울역에서 강남역"]}' --memo "출장"
```

**자동 분류 규칙 활용:**
- `rules` 커맨드의 `requirement_answer` 값이 있으면 TEXT 타입 필수항목의 답으로 활용 가능
- IT서비스(12532), 멤버십(70602), 매거진(12536)은 `isRequired: false`여도 자동 제출 시 필수항목 답변을 채운다

**필수항목 미입력 시**: 400 Bad Request 에러 반환 (이전에는 500이었으나 2026-04 수정됨)

**이미 제출된 건(SUBMITTED) 변경**: `update` 커맨드로 가능 (위 3-1). 2026-04에는 500이었으나 2026-11-09 V2 PUT으로 용도·필수항목·참석자 변경 성공을 재조회로 확인했다. 제출 취소 API는 여전히 없다 (DELETE, cancel 모두 404).

## 주의사항

- 이 헬퍼는 **본인 경비만** 다루도록 로컬에서 검사한다(위 "보안 한계" 참고: 인증은 아님)
- API 키는 회사 공용입니다. 외부에 절대 공유하지 마세요
- 제출 후 Gowid에서 관리자 승인을 기다리면 됩니다
- `submit`은 제출 직전 상태를 확인해 이미 제출된 건을 건너뜁니다(`skipped`). 동시에 두 번 실행하는 경합까지 서버가 막아 주지는 않으므로 같은 건을 병렬로 제출하지 않는다. 변경은 `update`
- 필수항목 있는 용도도 `--requirements`로 API 제출 가능. 필수항목 값은 사실만 넣고, 모르면 사용자에게 묻는다 (`auto_rules`의 `IT서비스 정기결제` 같은 자리표시 답을 다른 용도에 쓰지 않는다)

## 가맹점이 불분명할 때

- `인터넷결제_KPN_N`, `이노페이(비)_…`, `자동결제_N`, `정기과금_N` 은 PG(결제대행) 표기라 실제 상점을 알 수 없다. 사용자에게 롯데카드 카카오톡 알림 캡처를 받아 같은 금액·승인시각(`일시불, MM/DD HH:MM`)으로 실제 상점을 찾는다. 긴 캡처는 macOS Vision OCR(Swift `VNRecognizeTextRequest`, ko-KR)로 세로 타일링해 읽으면 된다
- `(주)고위드 - 자동결제` 는 고위드 노트북 대여료(매월 5일 정기, 노트북 대여 72017)가 기본. 금액이 평소와 다르면 반납 추가비용·매입 등 사유를 묻는다
- 서울보증보험 결제는 사이트(sgic.co.kr 법인 로그인 → 조회 → 보험계약 조회 → 기간별 현황)에서 금액으로 계약을 찾아 사업명을 필수항목에 적는다
- 과거 같은 가맹점 처리 이력은 `my-expenses --month`로 본인 건을 월별로 확인한다

## 테스트

외부 네트워크·실제 키 없이 로컬 mock 서버로만 돈다:

```bash
python3 -m unittest discover -s gowid-expense/tests -v
```
