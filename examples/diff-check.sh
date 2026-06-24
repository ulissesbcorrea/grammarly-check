#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Check staged git diff for grammar/style issues (LanguageTool backend)
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

git diff --cached --diff-filter=AM -- \
    '*.tex' '*.md' '*.txt' '*.rst' \
    | grep '^+' \
    | sed 's/^+//' \
    | python3 "$SCRIPT_DIR/languagetool_check.py"
