#!/usr/bin/env python3
"""
BCG 영상제작 계약서 smoke test.

⚠️ **주의**: 이 예제는 `templates/media_contract.py`가 정상 실행되는지
확인하는 smoke test일 뿐, 기존 발송본과 100% 동일하지 않다.
레거시 `scripts/contracts/build_eo_media_contract_bcg.py`가 실제 발송본의
source of truth이며, 이 스킬은 **다음 BCG-like 건**(다른 광고주·출연자·
금액의 영상제작 계약)에 쓰기 위한 것이다.

주요 차이 (baseline과 의도적 gap):
- EO 주소 포맷: parties.py의 공식 표기 사용 (줄바꿈 없음)
- 기타 문구: 템플릿은 파라미터화된 깔끔한 버전

실행: python3 build_bcg.py
"""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

from lib.parties import EO_KOREA, PRAIN_GLOBAL
from templates.media_contract import build_media_contract


INTERNAL_MEMOS = [
    (
        "1. 프레인글로벌 사업자등록증 최신본 교환",
        "본 계약서에 기재된 프레인 법인정보는 2023년 10월 19일 남대문세무서 "
        "발급 사업자등록증(남대문-104-81-55432, 대표자 김평기)을 근거로 함. "
        "서명 전에 프레인 측에 현재 기준 최신 사업자등록증 교환을 요청하여 "
        "대표자·주소·법인등록번호 변경 여부 확인 필요. "
        "동시에 EO 사업자등록증(501-87-01653, 2026-03-11 발급본)도 같이 첨부하여 발송."
    ),
    (
        "2. 대금 지급 조건 (프레인 회신 대기)",
        "현 초안은 EO 표준안인 '선금 50% 체결 후 14영업일 + 잔금 50% 최종본 이후 14영업일' "
        "으로 작성. 프레인 측 내부 규정이 다를 수 있으므로(예: '검수 완료 후 30일 이내'), "
        "회신받은 후 최종 확정. 하도급법상 대금은 검사 완료 후 60일 이내 지급이 한도이므로 "
        "프레인 요청이 그 범위 내이면 수용 가능."
    ),
    (
        "3. BCG 코리아 파트너 4인 정식 성함 확인",
        "본 초안에는 '송지연, 박영호, 이중훈, 장진석'으로 표기. 이메일에서 확인된 표기와 "
        "일치하나, 파트너 당사자의 공식 명함/재직 증명 기준 성함과 한자 표기를 "
        "프레인(백민주 과장)을 통해 확인 권장. 특히 출연자 초상권 확보 책임이 파트너(프레인)에 "
        "귀속되므로, 서명 전 출연자 동의서 수령 여부도 같이 확인."
    ),
]

CHECKLIST = [
    "□ 본 내부 메모 페이지 삭제 완료 (마지막 페이지)",
    "□ 프레인 사업자등록증 최신본 수령 확인",
    "□ EO 사업자등록증 PDF 첨부",
    "□ 계약명·금액·기간·당사자 표기 최종 확인",
    "□ chiri(김중철)에게 최종 검토 요청 → 승인 → 프레인(백민주) 발송",
]


if __name__ == "__main__":
    build_media_contract(
        partner=PRAIN_GLOBAL,
        eo=EO_KOREA,
        project_name="[BCG 코리아 파트너 인터뷰 시리즈] 영상 제작 및 홍보",
        supply_price=41_000_000,
        korean_supply_price="사천일백만",
        korean_vat="사백일십만",
        korean_total="사천오백일십만",
        start_date="2026년 4월 24일",
        end_date="2026년 6월 30일",
        insert_shoot_date="2026년 4월 24일(금)",
        main_shoot_date="2026년 5월 28일(목)",
        longform_price=36_000_000,
        shorts_price=5_000_000,
        longform_price_korean="삼천육백만",
        shorts_price_korean="오백만",
        shorts_unit_price_korean="일백이십오만",
        deposit_korean="이천오십만",
        deliverables=[
            "1. 롱폼 인터뷰 영상 1편 제작",
            "2. 쇼츠(숏폼) 영상 4편 제작 (인물별 1편)",
            "3. EO Korea 유튜브 채널 업로드",
        ],
        cast="송지연, 박영호, 이중훈, 장진석 (BCG 코리아 파트너 4인)",
        ad_client="보스턴컨설팅그룹 코리아(BCG)",
        extra_cost_per_edit=550_000,
        extra_cost_korean="오십오만",
        eo_contact={"name": "김중철", "role": "한국사업총괄",
                    "email": "chiri@eoeoeo.net"},
        partner_contact={"name": "백민주", "role": "과장",
                         "email": "m_zuu@prain.com",
                         "phone": "02-3210-9657"},
        internal_memos=INTERNAL_MEMOS,
        checklist=CHECKLIST,
        output_path="~/Downloads/skill_test_bcg.docx",
    )
