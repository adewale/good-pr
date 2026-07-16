#!/usr/bin/env bash
# check-pr-readiness.sh
#
# Quick automated checks for common PR issues.
# Run from the root of the repo you're contributing to.
#
# Usage: bash check-pr-readiness.sh [base-branch] [pr-body-file]

set -euo pipefail

BASE="${1:-main}"
PR_BODY_FILE="${2:-}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PASS="✓"
WARN="⚠"
FAIL="✗"

echo "PR Readiness Check (comparing against $BASE)"
echo "============================================="
echo ""

# Check 1: Diff size
LINES_CHANGED=$(git diff "$BASE"...HEAD --stat | tail -1 | grep -oE '[0-9]+ insertion|[0-9]+ deletion' | grep -oE '[0-9]+' | paste -sd+ - | bc 2>/dev/null || echo "0")
if [ "$LINES_CHANGED" -gt 500 ]; then
    echo "$WARN  Large diff: $LINES_CHANGED lines changed. Consider splitting into smaller PRs."
elif [ "$LINES_CHANGED" -gt 0 ]; then
    echo "$PASS  Diff size: $LINES_CHANGED lines changed"
else
    echo "$FAIL  No changes detected against $BASE"
fi

# Check 2: Test files modified
TEST_FILES=$(git diff "$BASE"...HEAD --name-only | grep -icE '(test|spec|_test\.|\.test\.)' || true)
if [ "$TEST_FILES" -gt 0 ]; then
    echo "$PASS  Test files modified: $TEST_FILES"
else
    echo "$WARN  No test files modified. Does this change need tests?"
fi

# Check 3: Commit count
COMMIT_COUNT=$(git rev-list --count "$BASE"...HEAD 2>/dev/null || echo "0")
echo "$PASS  Commits: $COMMIT_COUNT"

# Check 4: Check for possible secrets in diff
SECRETS=$(git diff "$BASE"...HEAD | grep -iE '(api_key|secret|password|token)\s*=' | head -5 || true)
if [ -n "$SECRETS" ]; then
    echo "$FAIL  Possible secrets in diff:"
    echo "$SECRETS" | sed 's/^/       /'
else
    echo "$PASS  No obvious secrets in diff"
fi

# Check 5: Console/debug statements
DEBUG=$(git diff "$BASE"...HEAD | grep -E '^\+' | grep -iE '(console\.log|debugger|binding\.pry|import pdb|print\()' | head -5 || true)
if [ -n "$DEBUG" ]; then
    echo "$WARN  Possible debug statements in diff:"
    echo "$DEBUG" | sed 's/^/       /'
else
    echo "$PASS  No debug statements detected"
fi

# Check 6: UI files changed (screenshots needed?)
UI_FILES=$(git diff "$BASE"...HEAD --name-only | grep -icE '\.(jsx|tsx|vue|svelte|css|scss|html|erb)$' || true)
if [ "$UI_FILES" -gt 0 ]; then
    echo "$WARN  $UI_FILES UI-related files changed — include captioned before/after screenshots, or explain why pixels do not change"
else
    echo "$PASS  No UI files changed"
fi

# Check 7: Audit drafted visual evidence when a PR body is supplied
if [ -n "$PR_BODY_FILE" ]; then
    if [ ! -f "$PR_BODY_FILE" ]; then
        echo "$FAIL  PR body file does not exist: $PR_BODY_FILE"
    elif ! command -v python3 >/dev/null 2>&1; then
        echo "$WARN  python3 is unavailable; skipped visual-evidence audit"
    else
        EVIDENCE_KIND="auto"
        if [ "$UI_FILES" -gt 0 ]; then
            EVIDENCE_KIND="ui"
        fi
        echo ""
        if python3 "$SCRIPT_DIR/check-visual-evidence.py" --kind "$EVIDENCE_KIND" "$PR_BODY_FILE"; then
            echo "$PASS  Visual-evidence audit completed"
        else
            echo "$FAIL  Visual-evidence audit found blocking issues"
        fi
    fi
elif [ "$UI_FILES" -gt 0 ]; then
    echo "$WARN  Pass a PR body file as argument 2 to audit its visual evidence"
fi

echo ""
echo "Done. Address any $WARN warnings and $FAIL failures before submitting."
