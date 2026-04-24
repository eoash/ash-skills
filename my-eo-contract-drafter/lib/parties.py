"""
EO 계약서 당사자 정보 레지스트리.

스키마:
    name (str)       — 한글 상호
    name_en (str)    — 영문 상호 (해외 계약용)
    business_no (str) — 사업자등록번호 (하이픈 포함)
    corporate_no (str|None) — 법인등록번호 (있으면)
    ceo (str)        — 대표자 성함
    address (str)    — 본점/사업장 소재지 (계약서 서명란용)
    contact (dict|None) — 실무 담당자 {name, role, email, phone}

새 거래처 추가 시 `memory/reference_<거래처>_legal.md` 파일을 먼저 만들고,
이 레지스트리는 그 파일의 사실만 복제한다 (환상 금지 — AI가 임의 추측한 정보 금지).
"""


EO_KOREA = {
    "name": "주식회사 이오스튜디오",
    "name_en": "EO Studio Inc.",
    "business_no": "501-87-01653",
    "corporate_no": "110111-7470563",
    "ceo": "김태용",
    "address": "서울특별시 강남구 압구정로28길 9-2, 4층 (신사동)",
    "address_en": (
        "4F, 9-2, Apgujeong-ro 28-gil, Gangnam-gu, Seoul, Republic of Korea"
    ),
    "bank": {
        "bank_name": "우리은행",
        "account": "1005-403-956285",
        "holder": "주식회사 이오스튜디오",
    },
    "contacts": {
        "legal_signer": {"name": "김태용", "role": "대표이사",
                         "email": "ty@eoeoeo.net"},
        "business_kr": {"name": "김중철", "role": "한국사업총괄",
                        "email": "chiri@eoeoeo.net"},
        "finance": {"name": "안서현", "role": "Finance Lead",
                    "email": "ash@eoeoeo.net"},
        "business_us": {"name": "유건욱", "role": "미국사업총괄",
                        "email": "gwy@eoeoeo.net"},
    },
}


PRAIN_GLOBAL = {
    "name": "주식회사 프레인글로벌",
    "name_en": "PRAIN GLOBAL Inc.",
    "business_no": "104-81-55432",
    "corporate_no": "110111-2029802",
    "ceo": "김평기",
    "address": (
        "서울특별시 중구 칠패로 37, 12,14층 (봉래동1가, 에이취에스비씨빌딩)"
    ),
    "contacts": {
        # 담당자는 계약 건별로 바뀌므로 호출부에서 override 권장
        "default": {"name": "백민주", "role": "과장",
                    "email": "m_zuu@prain.com", "phone": "02-3210-9657"},
    },
    "notes": (
        "홍보대행사. EO Korea와 5년+ 다회 거래. 광고주 대신 EO와 직접 계약 체결."
    ),
}


MODOODOC = {
    "name": "모두닥 주식회사",
    "name_en": None,
    "business_no": "561-81-00765",
    "corporate_no": None,
    "ceo": "안무혁",
    "address": "서울특별시 강남구 테헤란로 10길 6,\n9층 좌측 (역삼동, 녹명빌딩)",
    "contacts": {
        "ceo": {"name": "안무혁", "role": "대표",
                "email": "moohyug@modoodoc.com", "phone": "010-6755-7980"},
        "ops": {"name": "이재인", "role": "경영지원팀",
                "email": "janelee@modoodoc.com"},
    },
}


# Registry for lookup by key string (편의용)
REGISTRY = {
    "eo_korea": EO_KOREA,
    "prain_global": PRAIN_GLOBAL,
    "modoodoc": MODOODOC,
}


def get_party(key):
    """레지스트리 key로 거래처 조회. 없으면 KeyError."""
    return REGISTRY[key]
