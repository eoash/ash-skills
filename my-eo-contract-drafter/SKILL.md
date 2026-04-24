---
name: my-eo-contract-drafter
description: EO Studio 표준 계약서 docx 생성기. "계약서 써줘", "영상제작 계약서", "클린본 라이선스", "2차 활용 계약" 같은 요청을 받으면 서식 헬퍼 + 법인정보 레지스트리 + 템플릿을 조합해 Word에서 바로 날인 가능한 docx 초안을 생성한다. 7단계 플레이북 강제 + docx 서식 표준(굴림/바탕 10pt, 여백 상 3·하 2·좌우 2.5cm) 준수 + 내부 검토 메모 페이지 자동 부착.
type: custom
---

# EO Contract Drafter Skill

> ⚠️ **WIP — 2026-04-25**: `templates/media_contract.py`만 작성됨.
> `templates/secondary_use.py`, `examples/build_bcg.py`, `examples/build_modoodoc.py`는 아직 미작성.
> 회귀 검증(`/tmp/deslop_baseline/fingerprint.py`) 통과 전.
> **이 스킬은 아직 호출하지 말 것** — 레거시 `scripts/contracts/build_eo_*.py` 계속 사용.

## 언제 쓰는가 (When to use)

**트리거 키워드**: "계약서", "영상제작 계약", "홍보계약", "클린본 라이선스",
"2차 활용", "브랜디드 계약", "EO 표준 계약" — 이 중 하나라도 포함되면 이 스킬 활성화.

**전제 조건**:
- 거래처가 `lib/parties.py` 레지스트리에 등록돼 있어야 한다 (없으면 먼저 추가)
- 7단계 플레이북(`memory/reference_contract_drafting_playbook.md`)을 우회하지 않는다

## 언제 쓰지 말아야 하는가 (When NOT to use)

- **이미 발송된 계약서 수정** → `scripts/contracts/replace_modoodoc_body.py` 패턴의
  in-place string replace 경로 사용. 이 스킬은 **초판 생성 전용**.
  (근거: `.claude/rules/contract-docx.md`)
- **EO 표준 구조를 벗어난 계약서** (예: 주주간 계약, 투자계약, NDA) →
  Lisa legal advisor + 별도 템플릿 검색
- **당사자 정보 불확실** → 먼저 `memory/reference_<거래처>_legal.md` 수집부터

## 디렉토리 구조

```
.claude/skills/my-eo-contract-drafter/
├── SKILL.md                    # 이 파일
├── lib/
│   ├── eo_docx.py              # docx 서식 헬퍼 (폰트·여백·표·페이지)
│   └── parties.py              # 법인정보 레지스트리 (EO·프레인·모두닥)
├── templates/
│   ├── media_contract.py       # 영상제작 및 홍보계약서 (14조 + 별지 2호)
│   └── secondary_use.py        # 클린본 2차 활용 라이선스 (10조 + 별지 1호)
└── examples/
    ├── build_bcg.py            # BCG 건 재현 (legacy 호환 테스트)
    └── build_modoodoc.py       # 모두닥 건 재현 (legacy 호환 테스트)
```

## 사용법 (I/O 계약)

### 영상제작 계약서

```python
from lib.parties import EO_KOREA, PRAIN_GLOBAL
from templates.media_contract import build_media_contract

path = build_media_contract(
    partner=PRAIN_GLOBAL,      # dict (상호·사업자번호·주소·서명자·담당자)
    eo=EO_KOREA,
    project_name="[BCG 코리아 파트너 인터뷰 시리즈] 영상 제작 및 홍보",
    supply_price=41_000_000,   # int — VAT 별도
    start_date="2026년 4월 24일",
    end_date="2026년 6월 30일",
    deliverables=[
        "1. 롱폼 인터뷰 영상 1편 제작",
        "2. 쇼츠 영상 4편 제작 (인물별 1편)",
        "3. EO Korea 유튜브 채널 업로드",
    ],
    cast="송지연, 박영호, 이중훈, 장진석 (BCG 코리아 파트너 4인)",
    ad_client="보스턴컨설팅그룹 코리아(BCG)",
    eo_contact={"name": "김중철", "role": "한국사업총괄",
                "email": "chiri@eoeoeo.net"},
    internal_memos=[...],       # 리스트[(제목, 본문)] — 내부 검토 메모 페이지
    checklist=[...],            # 발송 전 체크리스트
    output_path="~/Downloads/파일명.docx",  # expanduser 권장 (Mac/Windows 호환)
)
```

반환: 생성된 docx의 절대경로.

### 클린본 2차 활용 라이선스 계약서

```python
from lib.parties import EO_KOREA, MODOODOC
from templates.secondary_use import build_secondary_use_contract

path = build_secondary_use_contract(
    partner=MODOODOC,
    eo=EO_KOREA,
    original_contract_date="2025년 8월 12일",
    original_project_name="모두닥 다큐멘터리",
    original_video_url="https://youtu.be/TdyJD6zfDUo",
    original_upload_date="2025년 10월 20일",
    supply_price=5_000_000,
    usage_purpose="\"파트너\"의 채용광고 용도",
    usage_media="YouTube, Meta..., TikTok, LinkedIn 등 — 제한 없음",
    duration="무기한",
    ...
)
```

## 7단계 플레이북 체크

이 스킬이 활성화되면 다음을 **대화에서** 완료한 뒤 생성 호출:

1. contract-review 4단계 프레임워크 진입 선언
2. Lisa legal lens 소환 (`/consult legal`)
3. 조회 7건: Gmail + EO 법인정보 + 거래처 법인정보 + eo-templates.ts +
   eo-contract-samples.txt + docx 서식 표준 + 4/7 학습 스레드
4. Stage 1~4 검증 (계약기간 / 손배cap / 수정횟수 / 비밀유지·DB미제공 / 불가항력)
5. EO 표준 구조 복제 (일반 템플릿 금지)
6. 법인정보 주입 — `lib/parties.py`에서만 추출 (환상 금지)
7. 생성 호출 → 내부 검토 메모 페이지 부착

## 서식 표준 (고정)

- 페이지: A4, 여백 상 3 / 하 2 / 좌우 2.5 cm
- 제목: 굴림 18pt Center Bold
- 조항 제목: 굴림 10pt Bold (`제 1 조【 계약의 목적 】`)
- 본문: 바탕 10pt Justify, 줄간격 1.23
- 항 번호: 원문자 `①②③...` 또는 `1) 2) 3)` (left_indent 0.5/1.0cm)
- 탭 문자 금지 (단락 속성으로 들여쓰기)
- 셀 라벨: 배경 #F2F2F2 + 중앙 정렬 + 셀 여백 주입 (OOXML `w:shd`·`w:tcMar`)

## 회귀 검증

기존 계약서와 바이너리 동일성은 **보장되지 않는다** (python-docx의 zip 압축은 비결정론적).
대신 paragraph/table fingerprint로 의미 등가 검증:

```bash
python3 /tmp/deslop_baseline/fingerprint.py <원본.docx> > baseline.json
python3 /tmp/deslop_baseline/fingerprint.py <생성본.docx> > current.json
diff baseline.json current.json
```

diff가 비어있으면 의미상 동일. `examples/build_bcg.py`와 `examples/build_modoodoc.py`는
이 등가성을 **테스트 케이스**로 박아둔 것이다.

## 관련 자산

- `memory/reference_contract_drafting_playbook.md` — 7단계 플레이북 (원본)
- `memory/reference_eo_korea_corporate_info.md` — EO 한국법인 공식 정보
- `memory/reference_prain_global_legal.md` — 프레인글로벌
- `memory/reference_modoodoc_legal.md` — 모두닥
- `memory/feedback_contract_drafting_failures_20260413.md` — Rocky 실패 오답노트
- `.claude/rules/contract-docx.md` — 발송 후 수정 금지 + 3단 백업 규칙
- `scripts/contracts/` — **레거시 초판 생성 스크립트** (deprecated after 2026-04-25)
