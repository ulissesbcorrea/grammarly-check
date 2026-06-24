#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# grammarly-check — check staged git diff for grammar/style issues
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# Extract added lines from the staged diff, strip the leading `+`,
# and pipe everything to grammarly-check.
git diff --cached --diff-filter=AM -- \
    '*.tex' '*.md' '*.txt' '*.rst' \
    | grep '^+' \
    | sed 's/^+//' \
    | python3 grammarly_check.py
