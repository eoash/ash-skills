---
name: my-cash-position
description: Cash Position 자동 업데이트. Plaid API로 Chase/Hanmi 은행 잔액·입출금 조회 + Google Sheets 자동 업데이트. "캐시", "cash", "잔액", "cash position" 요청에 사용.
triggers:
  - "캐시"
  - "cash"
  - "잔액"
  - "cash position"
  - "현금"
---

# Cash Position 자동 업데이트

Plaid API(Chase/Hanmi) + Clobe(한국) + 우리VN 데이터를 조회하여
Google Sheets Cash Position Summary를 업데이트하는 스킬.

## 핵심 스크립트

```
scripts/parse_cash_position.py
```

실행 환경: `/Users/ash/Documents/eoash/.venv/bin/python` (plaid, pandas, dotenv 설치됨)

## 사용법

### 1. 미국 은행만 (Plaid API — CSV 불필요)

```bash
/Users/ash/Documents/eoash/.venv/bin/python scripts/parse_cash_position.py \
  --plaid --month {YYYY.MM} [--dry-run] [--skip-revenue]
```

### 2. 전체 (한국 + 미국 + 베트남)

```bash
/Users/ash/Documents/eoash/.venv/bin/python scripts/parse_cash_position.py \
  --plaid \
  --clobe ~/Downloads/주식회사*.xlsx \
  --vietnam ~/Downloads/ExcelSheet*.xls \
  --month {YYYY.MM}
```

### 3. CSV 방식 (레거시 — Plaid 장애 시 fallback)

```bash
/Users/ash/Documents/eoash/.venv/bin/python scripts/parse_cash_position.py \
  --chase ~/Downloads/Chase*.CSV \
  --hanmi ~/Downloads/AccountHistory.csv \
  --clobe ~/Downloads/주식회사*.xlsx \
  --month {YYYY.MM}
```

## 실행 흐름

1. **사용자가 월을 지정하지 않으면** 현재 월(`YYYY.MM`)을 자동 사용
2. **먼저 `--dry-run`으로 실행**하여 결과 확인 (사용자에게 보여주기)
3. 사용자가 확인하면 **`--dry-run` 없이 재실행**하여 Google Sheets 실제 업데이트
4. 결과 요약: 각 법인 잔액, 입출금, US 합산, 환율

## 주요 옵션

| 옵션 | 설명 |
|------|------|
| `--plaid` | Chase/Hanmi를 Plaid API로 조회 (CSV 불필요) |
| `--clobe` | 한국 Clobe.ai 엑셀 파일 경로 |
| `--vietnam` | 우리은행 베트남 xls 경로 |
| `--techcombank` | Techcombank 베트남 CSV 경로 |
| `--month` | 대상 월 (예: 2026.03) — **필수** |
| `--skip-revenue` | 미국 매출/한국 미수금 업데이트 건너뜀 |
| `--dry-run` | 시트 업데이트 없이 결과만 출력 |
| `--extra-kr-balance` | 클로브에 없는 한국 계좌 잔액 수동 추가 |

## 환경변수 (.env)

스크립트가 자동으로 프로젝트 루트 `.env`를 로드함:
- `PLAID_CLIENT_ID` / `PLAID_SECRET` / `PLAID_ENV=production`
- `PLAID_ACCESS_TOKEN_CHASE` — Chase PLAT BUS CHECKING ...6797
- `PLAID_ACCESS_TOKEN_HANMI` — Hanmi Business Regular Checking ...3389
- Google Sheets SA: `finance-dashboard/.env.local`

## 주의사항

- `--dry-run` 없이 실행하면 Google Sheets가 직접 수정됨 — 반드시 먼저 dry-run
- Plaid access_token은 영구 토큰이지만, 은행 비밀번호 변경 시 재연결 필요
- 한국/베트남은 여전히 파일 필요 (Clobe 엑셀, 우리은행 xls)
