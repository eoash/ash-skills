# gowid-expense

Gowid 법인카드 경비를 Claude Code에서 자연어로 조회·제출하는 스킬.

> "내 미제출 경비 보여줘" → 조회 → "1번 식비로 제출해" → 완료

## 설치

```bash
npx skills add EO-Studio-Dev/gowid-expense-skill --skill gowid-expense -y
```

## 셋업 (1회)

**Mac / Linux:**
```bash
# ~/.zshrc 또는 ~/.bashrc에 추가
export GOWID_API_KEY="your_api_key"
```

**Windows (PowerShell):**
```powershell
# $PROFILE에 추가 (notepad $PROFILE)
$env:GOWID_API_KEY="your_api_key"
```

API 키는 Slack `#dev-ops` 채널의 고정 메시지를 확인하세요.

## 사용법

Claude Code에서 자연어로 요청:

| 요청 | 하는 일 |
|------|---------|
| "내 경비 보여줘" | 미제출 경비 조회 |
| "이거 IT서비스로 제출해" | 용도 지정 + 제출 |
| "용도 목록" | 사용 가능한 경비 카테고리 |
| "팀원 목록" | 참석자 선택용 (식비) |
| "자동규칙 검색 카카오" | 가맹점별 자동 분류 규칙 |

## 작동 방식

1. `git config user.email`로 본인 식별 (Gowid 계정과 매칭)
2. Gowid REST API 호출로 미제출 경비 조회
3. Claude가 대화형으로 용도 추천 + 제출 처리
4. 이미 제출된 건은 자동으로 건너뜀 (중복 제출 방지)

## 지원 기능

- **경비 조회**: 본인 카드의 미제출 내역
- **경비 제출**: 용도 지정 + 메모 + 참석자 (식비)
- **상세 조회**: 카드번호, 승인일, 금액, 현재 상태
- **용도 목록**: 58개 활성 카테고리
- **팀원 목록**: 참석자 선택용
- **자동규칙**: 가맹점별 자동 분류 규칙 검색 (289개)
- **규칙 제안**: GitHub Issue로 새 규칙 제안

## 자주 쓰는 용도

| 용도 | 비고 |
|------|------|
| 점심식비 | 인당 12,000원, 초과 시 참석자 필요 |
| 야근식비 | 인당 12,000원 |
| IT서비스 이용료 | 메모에 서비스명 (예: Notion, Slack) |
| 업무교통비 | 출발지/도착지 |
| 도서구입비 | |
| 소모품비(10만원이하) | |

## 요구사항

- [Claude Code](https://claude.ai/claude-code) 설치
- Python 3.9+
- Gowid 법인카드 계정 (이메일 매칭)
- `GOWID_API_KEY` 환경변수

## 구조

```
gowid-expense/
├── SKILL.md              # Claude Code 스킬 정의
├── scripts/
│   └── gowid.py          # Gowid API 헬퍼 (Python, 외부 패키지 불필요)
├── data/
│   └── auto_rules.json   # 자동 분류 규칙 (289개)
├── README.md
└── LICENSE               # MIT
```

## 라이선스

MIT
