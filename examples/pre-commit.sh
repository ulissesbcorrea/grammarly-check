#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Pre-commit hook: run grammarly-check on staged .tex / .md files.
#
# Install:
#   ln -sf ../../.githooks/pre-commit .git/hooks/pre-commit
#   # or use  cp examples/pre-commit.sh .git/hooks/pre-commit
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

STAGED=$(git diff --cached --diff-filter=AM --name-only -- '*.tex' '*.md' '*.txt' || true)

if [ -z "$STAGED" ]; then
    exit 0
fi

echo "🔍 grammarly-check: reviewing staged files …"

# Extract all added lines from staged diffs and pipe them to the checker.
git diff --cached --diff-filter=AM -- '*.tex' '*.md' '*.txt' \
    | grep '^+' \
    | sed 's/^+//' \
    | python3 grammarly_check.py \
    || true

echo "✅ grammarly-check finished."
