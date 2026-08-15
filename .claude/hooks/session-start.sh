#!/bin/bash
# SessionStart hook: install deps and build dist/ so the project is ready
# (typecheck/build work) as soon as a Claude Code on the web session starts.
set -euo pipefail

# Only run in the remote (web) environment; local sessions manage deps themselves.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

# Idempotent: safe to run on startup/resume/clear/compact. `npm install` (not
# `npm ci`) lets the cached container state be reused across runs.
npm install --no-audit --no-fund
npm run build
