#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Pre-commit hook: run languagetool-check on staged .tex / .md files.
#
# Install:
#   ln -sf ../../.githooks/pre-commit .git/hooks/pre-commit
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CHECKER="$SCRIPT_DIR/languagetool_check.py"
STAGED=$(git diff --cached --diff-filter=AM --name-only -- '*.tex' '*.md' '*.txt' || true)

if [ -z "$STAGED" ]; then
    exit 0
fi

echo "🔍 languagetool-check: scanning staged files …"

for f in $STAGED; do
    python3 "$CHECKER" --detex --file "$f" || true
done

echo "✅ languagetool-check finished."
