---
name: eo-video-pipeline
description: EO Studio 영상 편집 자동화 파이프라인 — Gemini 2.5 Flash + FCPXML, 자동화 확장 완료
type: project
---

EO 인터뷰 원본(3시간 × 3캠)을 AI로 분석하여 PD가 바로 편집할 수 있도록 정리하는 파이프라인.

**레포**: https://github.com/eoash/eo-video-pipeline
**로컬**: `/Users/ash/Documents/eo-video-pipeline`
**venv**: `.venv/` (google-genai, google-api-python-client 등 설치 완료)

**완성된 모듈**:
- `src/analyzer.py` — Gemini File API 영상 분석 (30분 단위 분할, structured JSON output)
- `src/fcpxml.py` — Final Cut Pro FCPXML v1.11 마커 생성 (테스트 통과)
- `src/sheets.py` — Google Sheets 4탭 자동 기록 (Index/Key Moments/Segments/Chapters)
- `src/drive.py` — Google Drive 폴더 감시 + 상태 파일 중복 방지
- `src/slack_notify.py` — Slack Incoming Webhook 알림 (Block Kit, 분석 완료 시 PD 알림)
- `src/audio_extract.py` — 2GB 초과 영상 자동 ffmpeg 오디오 추출 (m4a/AAC 128kbps)
- `src/nas_watch.py` — NAS 폴더 실시간 감시 (fswatch + polling fallback, 파일 안정성 감지)
- `src/checkpoint.py` — 5단계 idempotent resume 체크포인트 (실패 시 마지막 성공 단계부터 재개)
- `pipeline.py` — CLI 오케스트레이터 (analyze / watch / watch-nas 모드, 체크포인트 기반 resume)

**인프라**:
- `com.eostudio.video-pipeline.plist` — macOS launchd 데몬 (KeepAlive, ThrottleInterval=30)
- `scripts/launchd-install.sh` — 데몬 설치 스크립트
- `.env` 필요 변수: `GEMINI_API_KEY`, `SLACK_WEBHOOK_URL`, `NAS_WATCH_DIR`, `SHEETS_SPREADSHEET_ID`

**모델**: `gemini-2.5-flash` (2.0-flash는 deprecated)

**첫 분석 성공 (2026-03-14)**:
- 테스트 영상: `[EP1+2] Po Shen Loh_clean.m4v` (27분, 3.7GB)
- 영상→오디오 추출 후 분석 (3.7GB → 25MB m4a, ffmpeg 사용)
- 결과: 18,634자 트랜스크립트, 핵심 발언 20개, 주제 구간 13개, 챕터 6개, FCPXML 마커 26개
- GCP 프로젝트 `ash-email-487014` 결제(크레딧) 연결 완료

**주의사항**:
- Gemini File API REST 업로드 한도 2GB → 큰 영상은 ffmpeg으로 오디오 추출 필수
- 화자 감지가 1명만 될 수 있음 → 프롬프트 튜닝 여지

**Why:** PD가 3시간 원본에서 15분 편집본 만들 때 자료화면 찾기가 최대 병목. AI가 transcript + 핵심 발언 + 챕터 제안을 자동 생성하면 편집 시간 대폭 단축.

**How to apply:** `cd /Users/ash/Documents/eo-video-pipeline && source .venv/bin/activate && python pipeline.py analyze <파일경로>`

**남은 작업**:
- [ ] FCPXML을 Final Cut Pro에서 열어서 마커 확인
- [ ] Google Sheets 연동 (SHEETS_SPREADSHEET_ID 설정)
- [x] Drive watch 모드 + launchd 상시 실행 → NAS watch + launchd plist로 대체
- [ ] 화자 분리 개선 (인터뷰어 + 게스트)
- [ ] Slack Webhook URL 발급 + .env 등록
- [ ] 실제 3시간 원본 테스트
- [ ] fswatch 설치 (`brew install fswatch`)

**EO 영상 패턴** (분석 완료):
- 구조: Intro → Chapter 1~4 → 클로징 (4~6챕터, 각 2~5분)
- 유형: 1:1 대표 인터뷰 / 해외 강연 재편집
- 편집 도구: Final Cut Pro (주) + Premiere Pro
- PD: 김지환, 김도원, 남희주, 태용
