---
name: PR 생성 후 자동 머지
description: PR 생성 후 gh pr merge로 CLI에서 바로 머지까지 처리. GitHub 웹 UI에서 수동 머지 불필요.
type: feedback
---

PR 생성 후 `gh pr merge --merge --delete-branch`로 CLI에서 바로 머지까지 처리할 것.

**Why:** 혼자 작업하는데 매번 GitHub 웹에서 머지 버튼 누르는 게 번거로움. 단, 퍼블릭 서비스(token-dashboard 등)이므로 PR 자체는 유지 — 변경 이력 추적 + 롤백 안전장치.

**How to apply:** 브랜치 → PR 생성 → 바로 `gh pr merge` 실행. 사용자에게 "머지할까요?" 묻지 않고 자동으로 진행.
