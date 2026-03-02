---
name: flip-tracker
description: Flip 투자자 서명 회신 현황을 Gmail에서 자동으로 추적한다. 누가 회신했고, 누가 안 했는지, 첨부파일(서명본)이 왔는지 확인한다. "flip tracker", "서명 회신 확인", "플립 현황", "투자자 회신" 요청에 사용.
triggers:
  - "flip tracker"
  - "서명 회신 확인"
  - "플립 현황"
  - "투자자 회신"
  - "누가 회신했어"
  - "서명 왔어"
---

# Flip Tracker

투자자 16명/개사에게 발송한 Flip 서명 요청 메일의 회신 현황을 실시간으로 추적하는 스킬.

- 마감: **2026-02-27(금) 17:00 KST**
- 대상: 기관(한국) 7개사 + 기관(미국) 1개사 + 개인(거주자) 5명 + 개인(비거주자) 3명 = **총 16개**

---

## 실행 방법

### 1단계: 스크립트 실행

```bash
python C:/Users/ash/.claude/skills/flip-tracker/scripts/flip_tracker.py
```

토큰 파일은 아래 순서로 자동 탐색:
1. `C:/Users/ash/ash/token_send.json`
2. `C:/Users/ash/.claude/skills/my-context-sync/scripts/google_token.json`
3. `C:/Users/ash/ash/token.json`

### 2단계: 결과 파싱 및 보고

스크립트 출력을 파싱하여 아래 형식으로 사용자에게 보고한다.

---

## 출력 포맷

```
📊 Flip 서명 회신 현황 — YYYY-MM-DD HH:MM 기준
마감까지 N일 남음 (2026-02-27 17:00)

전체 16개 | 회신 N개 | 미회신 N개
첨부파일(서명본) 수신 N개

[완료] N개
  ✅ (주)퓨처플레이 (기관/한국) 📎서명본첨부
  ✅ 김성훈 (개인/거주자) — 2026-02-22

[미회신] N개 — 독촉 필요
  ⏳ ㈜데이터블 (기관/한국)
  ⏳ 장원준 (개인/거주자)
  ...
```

---

## 작동 원리

1. Gmail에서 `from:ash@eoeoeo.net subject:"EO Studio"` 로 발송한 Flip 스레드 탐색
2. 각 스레드에서 내 메시지 외 다른 발신자 메시지 존재 시 → **회신 완료**
3. 회신 메시지에 첨부파일 있으면 → **서명본 수신**
4. 발신자 이름/이메일을 INVESTORS 키워드와 매칭하여 투자자 특정

---

## 연결 상태

- ✅ Gmail API: `token_send.json` (gmail.readonly + gmail.send 스코프)
- ✅ 투자자 목록: 16명/개사 하드코딩 (flip_tracker.py INVESTORS)
- ✅ 마감일: 2026-02-27 17:00 자동 카운트다운
