# my-gmail-attachment-extractor

Gmail에서 첨부파일을 자동으로 다운로드하고, 파일 타입별로 처리(압축해제, 텍스트 추출)하는 스킬.

## 사용 시나리오
- 변호사/회계사로부터 받은 계약서 패키지 일괄 다운로드
- 메일 첨부파일에서 텍스트 추출 후 분석
- ZIP 안의 문서들 자동 압축 해제 및 정리

## 실행 흐름

### Step 1: Gmail 검색
```
사용자 입력: 검색 쿼리 (예: "from:eugene subject:Flip has:attachment")
→ Gmail API로 매칭되는 메일 검색
→ 첨부파일 목록 출력
```

### Step 2: 다운로드
```
사용자 확인 후 첨부파일 다운로드
→ 저장 경로: docs/{project}/ 또는 사용자 지정 경로
→ ZIP 파일은 자동 압축 해제
```

### Step 3: 텍스트 추출 (선택)
```
--extract 옵션 시:
→ .docx → python-docx로 텍스트 추출
→ .pdf → PyPDF2로 텍스트 추출
→ 통합 텍스트 파일 생성 (all_extracted.txt)
```

## 의존성
- Gmail API (token_send.json)
- python-docx (docx 추출 시)
- PyPDF2 (pdf 추출 시)

## 상태: 초안 (구현 대기)
- 현재 `scripts/gmail_fetch.py` + 수동 docx 추출 코드가 분산되어 있음
- 이 스킬로 통합하면 반복 작업 제거 가능
