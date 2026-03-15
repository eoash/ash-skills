---
name: Anthropic 플랜 구조 — Admin API 사용 불가
description: claude.ai Team 플랜과 API Organization이 분리되어 있어 Admin API로 팀 Claude Code 사용량 조회 불가
type: project
---

EO Studio의 Anthropic 계정 구조 (2026-03-14 확인):
- **claude.ai Team 플랜**: 팀원 시트 구독, Claude Code 사용 — Admin API key 발급 메뉴 없음
- **API Organization** ("EO Stidio", API plan): `console.anthropic.com`에서 Admin key 발급 가능하지만 팀원 Claude Code 데이터 0건

**Why:** 두 시스템이 완전 분리. API Org의 Admin key(`sk-ant-admin...`)로 Team 플랜 사용량 조회 불가. Claude Code Analytics API (`/v1/organizations/usage_report/claude_code`)는 존재하지만 Team 플랜 데이터에 접근 못함.

**How to apply:**
- "Admin API로 hook 제거" 제안은 **현재 불가** — 제안하지 말 것
- Token Dashboard는 **hook 기반 아키텍처(otel_push.py) 유지 필수**
- hook 운영 비용 절감에 집중: launchd 전환, heartbeat, 자동 장애 감지
- Enterprise 플랜 전환 시 Admin API 재검토 가능 (비용 이슈)
- API Org의 Admin key는 token-dashboard `.env.example`에 정의되어 있지만 실제로는 사용 안 함
