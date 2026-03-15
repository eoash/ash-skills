---
name: finance-dashboard
description: Finance Dashboard 기술 상세 — 위드택스, VN 계좌, Cash Position 스크립트
type: project
---

## 기본 정보
- **배포**: https://finance-dashboard-opal-xi.vercel.app
- **데이터**: Google Sheets API + 위드택스 정적 데이터
- **페이지 7개**: Revenue, Clients, A/R, YoY, Cash, Income, FX
- **SA key**: `finance-dashboard/sa-key.json`
- **환율 API**: fawazahmed0/currency-api (KRW+VND historical, API key 불필요)
- **BUDGET_FX_RATE**: `utils.ts` 상수 1,450 — 한 곳 수정으로 전체 반영

## 위드택스 데이터 (세무법인 공식 회계)
- **Looker Studio**: `https://lookerstudio.google.com/s/mrHnGOvqVDQ`
- **데이터 파일**: `finance-dashboard/src/lib/withtax-data.ts`
- **용도**: Income Statement 전용
- **업데이트**: 월 1회 세무법인 결산 후 수동 반영 (last: 2026.01.21)
- **접근**: Playwright 브라우저, ash@eoeoeo.net

## Sheets 구조
- **_SYNC_ Staging Layer**: Apps Script → 클론 탭 → 대시보드 (현재연도=_SYNC_ 탭, 다른연도=원본 직접)
- **스크립트**: `scripts/sync-sheets.gs` (Web App Sync 버튼 수동 트리거)

## Cash Position 스크립트 (`scripts/parse_cash_position.py`)
- **은행**: 🇰🇷 우리/농협/국민(Clobe.ai), 🇺🇸 Chase/Hanmi(CSV), 🇻🇳 우리VN(xls)
- **Chase CSV 주의**: DEBIT/CREDIT가 index 흡수 → 컬럼 1칸 밀림 보정 필요
- **Clobe**: 연간 파일 월별 분리, 월말 잔액 역산
- **환율 자동화**: fawazahmed0 API → USD/KRW(Row22) + VND→KRW(Row37) 자동 입력

## VN 계좌 구조
- **계좌 1 (Operating)**: 100200613769 — 주 거래 계좌 (XLS 별도 다운로드)
- **계좌 2 (Investment)**: 거래 거의 없음
- Sheets Row 39~42: Operating, Row 44~47: Investment, Row 33~36: 합산 수식
