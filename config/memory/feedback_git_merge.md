---
name: git-merge-not-rebase
description: pull 시 rebase 대신 merge 사용 — 팀 전원 자동커밋(backfill)으로 rebase 충돌 위험
type: feedback
---

pull 시 `git pull` (merge) 사용, `git pull --rebase` 금지.

**Why:** 팀원 전원이 backfill 자동 커밋을 하므로 rebase 시 충돌 위험이 높고, 내 브랜치 커밋이 꼬일 수 있음. merge가 안전.

**How to apply:** push rejected 시 `git stash && git pull && git stash pop && git push` (rebase 플래그 없이).
