---
name: my-design-grade
description: EO 내부 웹 도구(대시보드·포털·리뷰툴)의 UI를 EO 공통 디자인(#0A0A0A/#00E87A)으로 채점하고 "비싸 보이게" 끌어올리는 디자인 self-grading 스킬. 8-pillar 체크리스트로 Strong/Mixed/Missing 진단 → batch-fix → 모션 패스. "디자인 채점", "UI 리뷰", "self-grading", "비싸 보이게", "디자인 polish", "/my-design-grade" 요청에 사용.
---

# my-design-grade

EO 내부 웹 도구의 한 화면을 "그냥 작동하는" 수준에서 **"비싸 보이고 빠르게 느껴지는"** 수준으로 끌어올리는 디자인 self-grading 스킬.

출처: Metics Media "Build $10,000 Websites using Claude Code"(2026-05-29)의 8-pillar 체크리스트 + self-grading 루프를 EO 공통 디자인 시스템에 맞게 구체화.

## 언제 쓰나

- contract-review · finance-dashboard · eo-portal · token-dashboard 등 내부 도구의 화면 품질을 올리고 싶을 때
- "이 화면 디자인 어때?", "UI 채점해줘", "더 비싸 보이게", "AI 티 빼줘" 같은 요청
- 새 화면을 만들기 전 품질 기준선을 잡고 싶을 때

## 핵심 철학 (3가지)

1. **기준을 먼저 못 박는다** — 만들기 전에 8기둥을 정의, 빌드 후 그 기준으로 채점.
2. **"무엇을 추가하라"가 아니라 "어떻게 느끼게 하라"** — intent over specifics.
3. **하나씩 말고 batch로** — 작은 수정 5개를 한 프롬프트에. 토큰 절약 + 응집력.

## 워크플로우

```
① self-grading(진단) → ② batch-fix(의도로 한 번에) → ③ drive-yourself(평평한 섹션 모션 1개씩) → 재채점
```
"전부 Strong"이 될 때까지 2~3회 반복.

## 실행 절차

1. **대상 화면 확인** — 어떤 도구의 어느 화면인지, 라이브 URL 또는 소스 경로 파악.
2. **전체 플레이북 로드** — `references/eo-design-self-grading.md`를 Read. 8-pillar 정의 + 3종 프롬프트(채점/batch-fix/모션)가 들어있다.
3. **① 채점** — §2 self-grading 프롬프트로 화면을 Strong/Mixed/Missing 등급. "be honest", 후하게 주지 말 것. 끝에 "가장 손이 필요한 3개"를 우선순위로.
4. **② batch-fix** — §3 프롬프트로 Mixed/Missing 항목을 intent로 한 번에 수정 제안 → 승인 → 일괄 적용.
5. **③ 모션 패스** — §4 프롬프트로 직접 스크롤하며 평평한 섹션을 찾아 섹션당 하나씩 절제된 인터랙션 추가. 노골적이면 "더 미묘하게".
6. **재채점** — ①로 돌아가 개선 확인.

## EO 가드레일 (항상 적용)

- 배경 `#0A0A0A`, 액센트 `#00E87A` **단 하나** (남발 금지)
- **Inter 폰트 금지**(AI-tell) → Geist/Pretendard
- **em-dash(—) 금지**(외부 카피 AI-tell) → 마침표·쉼표·콜론
- raw JSON / `**` 마크다운 화면 노출 금지
- API 미인증 = **401 JSON**(302 리다이렉트 금지)
- 날짜는 **KST 유틸**(`toISOString` 금지)
- 통화는 **`₩XXX · $YYY` 듀얼 표기**

상세 8-pillar 기준·프롬프트 전문 → `references/eo-design-self-grading.md`
