---
name: my-sync-us-revenue
description: 미국 매출 동기화 (Bill.com 인보이스 + Plaid 입금 매칭 → Google Sheets). "미국 매출", "US revenue", "입금 확인", "sync revenue", "미입금" 요청에 사용.
triggers:
  - "미국 매출"
  - "US revenue"
  - "입금 확인"
  - "sync revenue"
  - "미입금"
  - "매출 동기화"
---

# 미국 매출 동기화

Bill.com 신규 인보이스 + Plaid 은행 입금 → Google Sheets `2026 미국 매출` 시트 자동 동기화.

## 핵심 스크립트

```
scripts/daily/sync_us_revenue.py
```

실행 방법: `uv run` (launchd plist와 동일)

```bash
/opt/homebrew/bin/uv run \
  --with python-dotenv --with requests \
  --with google-auth --with google-api-python-client \
  scripts/daily/sync_us_revenue.py [--dry-run] [--year YYYY]
```

## 실행 흐름

### 1. 항상 dry-run 먼저

```bash
/opt/homebrew/bin/uv run \
  --with python-dotenv --with requests \
  --with google-auth --with google-api-python-client \
  scripts/daily/sync_us_revenue.py --dry-run
```

결과를 사용자에게 보여준다:
- 신규 인보이스 추가 건수
- 입금 매칭 건수 (Stripe/YouTube/콘텐츠)
- 미입금 목록

### 2. 사용자 확인 후 실행

dry-run 결과를 보고 사용자가 승인하면 `--dry-run` 없이 재실행:

```bash
/opt/homebrew/bin/uv run \
  --with python-dotenv --with requests \
  --with google-auth --with google-api-python-client \
  scripts/daily/sync_us_revenue.py
```

### 3. 결과 요약

실행 후 사용자에게 보여줄 것:
- 추가된 인보이스 건수
- 매칭된 입금 건수 + 회사명/금액
- 남은 미입금 목록
- Slack 알림 전송 여부

## 자동 실행 (launchd)

```
~/Library/LaunchAgents/net.eoeoeo.sync-us-revenue.plist
```

- **주기**: 매 1시간 (StartInterval: 3600)
- **로그**: `scripts/daily/sync_us_revenue.log` (RotatingFileHandler, 1MB x 3 백업)
- **stdout/stderr**: `scripts/daily/sync_us_revenue.stdout.log`, `.stderr.log`

## 동작 원리

1. **네트워크 체크** — `check_network()` DNS 사전 확인, 불가 시 조용히 종료
2. **Bill.com** — 로그인(재시도 2회) → 신규 인보이스 시트 추가
3. **Plaid** — Chase/한미 입금 조회 → Stripe/YouTube/콘텐츠 분류 → 시트 매칭
4. **중복 방지** — `already_matched` set으로 이미 입금 확인된 행의 Plaid 거래 소진
5. **Slack 알림** — 신규 입금 감지 시 `#all-프로젝트현황` 채널 자동 알림

Bill.com과 Plaid는 독립 실행 — 한쪽 실패해도 다른 쪽은 정상 동작.

## 주요 옵션

| 옵션 | 설명 |
|------|------|
| `--dry-run` | 시트 변경 없이 결과만 출력 |
| `--year` | 대상 연도 (기본: 올해) |

## 환경변수 (.env)

스크립트가 프로젝트 루트 `.env`를 자동 로드:
- `BILL_COM_USERNAME` / `BILL_COM_PASSWORD` / `BILL_COM_ORG_ID` / `BILL_COM_API_KEY`
- `PLAID_CLIENT_ID` / `PLAID_SECRET` / `PLAID_ACCESS_TOKEN_CHASE` / `PLAID_ACCESS_TOKEN_HANMI`
- `SLACK_BOT_TOKEN` — 입금 알림 전송용

## 주의사항

- `scripts/daily/`는 `.gitignore` 제외 — 로컬 전용, git 커밋 불가
- `--dry-run` 없이 실행하면 Google Sheets가 직접 수정됨
- 동일 금액 다건 매칭은 순서 의존 — 오매칭 의심 시 시트 수동 확인
- Slack 알림 채널: `C048XKTV5LK` (`#all-프로젝트현황`)

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| 4일+ 무알림 | macOS 잠자기 후 DNS 실패 연속 | stderr.log 확인, 맥북 네트워크 상태 점검 |
| 동일 금액 오매칭 | 미입금 행 순서 + 금액만 매칭 | 시트에서 잘못된 입금일 삭제 → 재실행 |
| Bill.com 로그인 실패 | API 크레덴셜 만료/변경 | `.env` 확인, Bill.com 대시보드에서 갱신 |
| Plaid 토큰 만료 | 은행 비밀번호 변경 | `python scripts/plaid_link_connect.py` 재연결 |
