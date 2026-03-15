---
name: token-dashboard
description: Token Dashboard 아키텍처, 핵심 패턴, 게이미피케이션 스펙
type: project
---

## 아키텍처
- Next.js 16 (App Router) + Recharts 3 + Tailwind v4
- 데이터: OTel Collector (Railway) → Prometheus (Railway) → Next.js (Vercel)
- Mock 모드: PROMETHEUS_URL 없으면 자동 전환
- **프로젝트별 CLAUDE.md**: `token-dashboard/CLAUDE.md` (파이프라인, 오답노트 등)

## 3개 AI 도구 파이프라인
| 도구 | 수집 | 저장 |
|------|------|------|
| Claude Code | otel_push.py (Stop hook) | OTel → Prometheus + backfill JSON |
| Codex CLI | codex_push.py (cron 2h) | REST API → backfill JSON |
| Gemini CLI | 네이티브 OTel | OTel Collector → Prometheus |

## 핵심 패턴
- **TEAM_MEMBERS**: 이메일→이름 매핑 (N:1). UI/Mock용은 UNIQUE_MEMBERS
- **resolveActorName**: 이메일 lowercase 정규화 + username fallback
- **NAME_TO_AVATAR**: Slack 프로필 사진 URL
- **aggregator**: name 기준 합산. lib/aggregators/ 에 6개 분리
- **backfill 우선**: backfill vs Prometheus 겹치는 (email,model,date)에서 큰 값 자동 선택
- **Prometheus 쿼리**: `increase()` 사용 금지 → 원본 카운터 시간별(step=3600) 조회 + JS delta 계산. `computeDailyIncrease()` in `prometheus.ts`
- **Codex input_tokens는 cached 포함**: Claude와 시맨틱 다름. backfill 저장 시 `input - cache_read` 차감 필수
- **backfill API는 merge 방식**: date+model 키로 기존 데이터 보존 (replace 금지)
- **cache_read 제외**: 토큰 집계/XP 계산에서 cache_read_tokens 미포함

## 설치 현황 (3/13 기준)
- backfill 있음 26명: ash, chaenn, chankim, chiri, cw.lim, grace, gyeol, heejoo, hungtran, hyeri, hyunahk, ivee, izzy, jemin, jhghood25, june, jy.lim, kairenz, leejumi, ljw, phoenix, saul, songsh, truonghpq.vd, ty, zen.park
- 미가입 8명: Kashy(diepngan), Dowon(dwkim), Gunwook(gwy), Jeebin(jeebin), Sumin(ksm), SoYoung(soyoung), Jade(yjk), Chanhee(chanhee)
- **ty**: 3/10 이후 미집계 — hook 재설치 필요 (3/13 Slack DM 발송)
- **chanhee**: backfill POST 한번도 성공 못함 — Windows install-hook.ps1 재실행 필요

## 게이미피케이션 (/rank) — AI Explorer's Log
- **세계관**: AI 세계 탐사 → 최종 AI Native Human이 되는 여정
- **레벨**: Scout(0) → Ranger(200) → Explorer(1.5K) → Pathfinder(6K) → Pioneer(20K) → Vanguard(60K) → Trailblazer(200K,심사) → AI Native(1M,심사)
- **XP 공식**: `(input+output)/10K + days×50 + commits×1 + PRs×30 + streak×10` (cache_read 제외)
- **XP Decay**: 7일 유예 → 일 1% 복리 감소 (DECAY_GRACE_DAYS=7, DECAY_RATE=0.01)
- **수동 심사제**: AUTO_LEVEL_CAP=6, PROMOTED_USERS dict에 이메일:레벨 등록
- **업적 38개**: 8 카테고리 (Launch Prep / Flight Log / Fuel / Cargo / Multi-Engine / Mission Commander / Flight Time / Altitude)
- **레벨 컬러**: Scout(#666) → Ranger(#4A9EFF) → Explorer(#00E87A) → Pathfinder(#00CED1) → Pioneer(#A855F7) → Vanguard(#F59E0B) → Trailblazer(#EF4444) → AI Native(#E8FF47→#00E87A)

## 테스트
- **vitest**: `npm test` (14 테스트), `npm run test:watch`
- 테스트 대상: `computeDailyIncrease()` + `tsToDate()` (`src/lib/__tests__/prometheus.test.ts`)
