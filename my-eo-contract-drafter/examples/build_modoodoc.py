#!/usr/bin/env python3
"""
모두닥 클린본 2차 활용 라이선스 계약서 재생성 예제.

목적: `templates/secondary_use.py`가 기존 레거시 스크립트
(`scripts/contracts/build_eo_secondary_use_contract.py`)와 의미 등가성을
보장하는지 회귀 검증.

실행: python3 build_modoodoc.py
검증: /tmp/deslop_baseline/mododoc_baseline.json과 fingerprint diff
"""
import sys
from pathlib import Path

# lib + templates를 모듈 경로에 추가
SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

from lib.parties import EO_KOREA, MODOODOC
from templates.secondary_use import build_secondary_use_contract


INTERNAL_MEMOS = [
    (
        "1. 거래 단가 근거 및 할인율 (내부 기록용)",
        "EO 플레이북 표준 단가: 클린본 = 원 공급가의 30% → 원 계약 공급가 4,000만원 기준 표준 단가는 "
        "1,200만원. 이번 합의는 500만원(원 공급가의 12.5%)으로 표준 대비 약 58% 할인. 할인 배경은 "
        "(a) 기간 무제한 조건 수용, (b) 기존 거래처 우대, (c) 2차 활용 건의 첫 실사례로 관행 정착 목적. "
        "향후 모두닥과의 후속 거래 또는 다른 거래처 단가 협상 시 '이번 건은 특수 조건'임을 명시해 "
        "표준 30%가 재협상의 기준점이 되지 않도록 관리 필요."
    ),
    (
        "2. 원 계약 잔금 완납 여부 — 확인 완료",
        "원 계약 제4조 잔금 이천이백만원은 서현님 구두 확인(2026-04-23) 기준 완납 상태. 본 2차 계약을 "
        "원 계약 '이행 완료 후 별도 체결'로 깔끔하게 처리 가능. 미완납이었다면 본 계약 체결 전 선결이 필요했음."
    ),
    (
        "3. 클린본 납품물 준비 상태 확인",
        "계약 체결 후 7영업일 이내 클린본 인도가 제6조 의무. 현재 클린본 파일(자막·로고·음악 제거본)이 "
        "편집 완료되어 있는지 송승환 PD에게 확인 필요. 편집 소요 시간이 있을 경우 계약 체결 일정을 "
        "해당 편집 완료 시점 이후로 조정하는 것이 안전."
    ),
    (
        "4. 원 계약서 제6조 제3항 광고수익 조항과의 정합성",
        "원 계약 제6조 3항은 '영상 유통과정에서 광고수익 등을 얻게 된 경우 EO에 귀속'으로 명시. 본 "
        "2차 계약에서 '파트너'가 2차 저작물로 집행하는 채용광고는 '광고수익'이 아닌 '채용 효과'에 "
        "해당하므로 해석상 무관. 다만 2차 저작물을 통해 YouTube 채널 광고수익(Adsense 등)이 직접 "
        "발생하는 구조라면 별도 문구 추가 필요 — 채용광고 용도이므로 실무상 문제 없을 가능성 높음."
    ),
    (
        "5. EO 보호조항(내림 요청권) 미포함 사유 — 기록용",
        "클린본은 정의상 EO 워터마크·로고·자막이 제거된 버전이므로 모두닥의 2차 저작물에 EO 브랜드가 "
        "노출될 경로가 없음. 따라서 사회적 물의 발생 시 'EO 요청으로 영상 내림' 조항의 방어 필요성이 "
        "상쇄됨(서현님 판단 2026-04-23). 대신 이용 목적을 '채용광고'로 한정하고, 재라이선스·재양도 "
        "금지(제7조)와 표시·광고 심사지침 준수(제3조 제2항)로 EO의 독립적 이해관계는 충분히 보호."
    ),
    (
        "6. 크레딧 표기 미요구 사유 — 기록용",
        "일반적 라이선스 거래에서는 '영상 출처: EO 모두닥 다큐멘터리' 등 크레딧 표기를 요구하나, "
        "이번 건은 서현님 판단(2026-04-23)으로 미요구. 클린본이 EO 브랜드가 제거된 상태이고, "
        "모두닥 채용광고 맥락상 EO 크레딧 노출이 오히려 광고 효과를 저해할 수 있음. 조항 불포함 정당."
    ),
    (
        "7. 모두사인 업로드 시 제목 및 서명 순서",
        "파일명: \"[EO]_영상클린본라이선스계약서_모두닥_20260423.docx\" → docx→pdf 변환 후 업로드. "
        "서명 순서: 모두닥(파트너) → EO 순. 원 계약 이재인 담당자(janelee@modoodoc.com)에게 "
        "요청서 발송. Modusign 기존 Document ID와는 별건으로 신규 생성."
    ),
    (
        "8. 송승환 PD 회신 약속(2026-04-22)",
        "송승환 PD가 '계약서 초안 송부 → 이후 클린본 공유' 순서로 안내함. 본 초안 서현님 검토 후 "
        "수정 완료되면 송승환 PD를 통해 모두닥 이재인에게 전달. EO 내부적으로 송승환 PD의 "
        "최종 확인 회신도 받는 것이 안전 (계약 당사자는 EO 법인이지만 실무 PD 인지 필요)."
    ),
]

CHECKLIST = [
    "□ 본 내부 메모 페이지 삭제 완료 (마지막 페이지)",
    "□ 계약명·금액·기간·당사자 표기 최종 확인",
    "□ EO 사업자등록증 PDF 첨부 (필요 시)",
    "□ 클린본 파일 준비 완료 여부 송승환 PD에게 확인",
    "□ 파일명 발송용으로 변경: [EO]_영상클린본라이선스계약서_모두닥_20260423.docx",
    "□ docx → pdf 변환 후 모두사인 업로드",
    "□ 송승환 PD → 모두닥 이재인(janelee@modoodoc.com) 발송 흐름 확인",
]


if __name__ == "__main__":
    build_secondary_use_contract(
        partner=MODOODOC,
        eo=EO_KOREA,
        original_contract_date="2025년 8월 12일",
        original_project_name="모두닥 다큐멘터리",
        original_video_url="https://youtu.be/TdyJD6zfDUo",
        original_upload_date="2025년 10월 20일",
        supply_price=5_000_000,
        korean_supply_price="오백만",
        korean_vat="오십만",
        korean_total="오백오십만",
        usage_purpose='"파트너"의 채용광고 용도',
        usage_purpose_short="채용 및 인재 유치를 위한 광고·마케팅",
        usage_media=(
            "YouTube, Meta(Facebook·Instagram), TikTok, LinkedIn 등 온라인 "
            "플랫폼 및 옥외·지하철·교통 등 오프라인 매체 — 제한 없음"
        ),
        duration="본 계약 효력 발생일부터 기한의 정함이 없음 (무기한)",
        eo_contact={"name": "송승환", "role": "PD",
                    "email": "songsh@eoeoeo.net"},
        partner_contact={"name": "이재인",
                         "email": "janelee@modoodoc.com"},
        internal_memos=INTERNAL_MEMOS,
        checklist=CHECKLIST,
        output_path="~/Downloads/skill_test_modoodoc.docx",
    )
