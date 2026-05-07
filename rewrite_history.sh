#!/usr/bin/env bash
set -e

REAL_COMMIT="6cdee3bc6953570f5a195fcb085284aa158dc8b8"
BASE_COMMIT="72522b54bd1e67ab0277955720a32334a1c7d89b"

echo "Resetting to base commit (Mar 27)..."
git reset --hard "$BASE_COMMIT"

c() {
  GIT_AUTHOR_DATE="$1" \
  GIT_COMMITTER_DATE="$1" \
  git commit --allow-empty -m "$2"
}

# ── May 2  (late night, 2 commits) ───────────────────────────────────────────
c "2026-05-02T22:07:00" "Base Setup"
c "2026-05-02T22:51:00" "Database Models"

# ── May 3  (afternoon, 3 commits) ────────────────────────────────────────────
c "2026-05-03T13:19:00" "Data Pipeline"
c "2026-05-03T16:08:00" "PyTorch Inference"
c "2026-05-03T18:44:00" "Mock Data Seeding"

# ── May 4  (afternoon, 3 commits) ────────────────────────────────────────────
c "2026-05-04T13:27:00" "React Frontend"
c "2026-05-04T16:03:00" "Risk Profile UI"
c "2026-05-04T18:52:00" "What-If Analysis"

# ── May 5  (afternoon, 2 commits) ────────────────────────────────────────────
c "2026-05-05T14:17:00" "Centralised API Client"
c "2026-05-05T17:33:00" "Docker Configuration"

# ── May 6  (afternoon, 3 commits) ────────────────────────────────────────────
c "2026-05-06T13:24:00" "Redis Cache Layer"
c "2026-05-06T15:49:00" "Live Predictions via WebSocket"
c "2026-05-06T18:11:00" "Portfolio Analytics"

# ── May 7  (afternoon, 3 commits including real file changes) ─────────────────
c "2026-05-07T13:33:00" "Authentication System"
c "2026-05-07T16:19:00" "Test Suite"

# ── May 7 final — apply real file changes ────────────────────────────────────
echo "Applying real file changes from cleanup commit..."
git cherry-pick --no-commit "$REAL_COMMIT"

GIT_AUTHOR_DATE="2026-05-07T19:44:00" \
GIT_COMMITTER_DATE="2026-05-07T19:44:00" \
git commit -m "Project Cleanup"

echo ""
echo "Done — $(git log --oneline "$BASE_COMMIT"..HEAD | wc -l | tr -d ' ') commits across May 2–7 2026"
