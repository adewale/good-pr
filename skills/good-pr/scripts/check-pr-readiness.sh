#!/usr/bin/env bash
# check-pr-readiness.sh
#
# Quick automated checks for common PR issues.
# Run from the root of the repo you're contributing to.
#
# Usage: bash check-pr-readiness.sh [base-branch] [pr-body-file] [auto|ui|generated|none]

set -euo pipefail

BASE="${1:-main}"
PR_BODY_FILE="${2:-}"
EVIDENCE_KIND="${3:-auto}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PASS="✓"
WARN="⚠"
FAIL="✗"
FAILURES=0

case "$EVIDENCE_KIND" in
    auto|ui|generated|none) ;;
    *)
        echo "error: evidence kind must be one of auto, ui, generated, or none" >&2
        exit 2
        ;;
esac

echo "PR Readiness Check (comparing against $BASE)"
echo "============================================="
echo ""

# Check 1: Diff size
LINES_CHANGED=$(git diff "$BASE"...HEAD --numstat | awk '{ insertions += $1; deletions += $2 } END { print insertions + deletions }')
CHANGED_FILES=$(git diff "$BASE"...HEAD --name-only | awk 'NF { count += 1 } END { print count + 0 }')
if [ "$LINES_CHANGED" -gt 500 ]; then
    echo "$WARN  Large diff: $LINES_CHANGED lines changed. Consider splitting into smaller PRs."
elif [ "$LINES_CHANGED" -gt 0 ]; then
    echo "$PASS  Diff size: $LINES_CHANGED lines changed"
elif [ "$CHANGED_FILES" -gt 0 ]; then
    echo "$PASS  Non-text or binary-only diff: $CHANGED_FILES file(s) changed"
else
    echo "$FAIL  No changes detected against $BASE"
    FAILURES=1
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

# Check 4: Check added lines for possible secrets. This remains advisory because
# lexical matches include fixtures and examples; never print the candidate value.
SECRETS=$(git diff "$BASE"...HEAD -U0 | grep -E '^\+' | grep -vE '^\+\+\+' | grep -iE '(api[_-]?key|secret|password|token)[[:space:]]*[:=][[:space:]]*["'\''][^"'\'']+' | head -5 || true)
if [ -n "$SECRETS" ]; then
    echo "$WARN  Possible secret assignment added; inspect the diff before publishing (value redacted)"
else
    echo "$PASS  No obvious secrets in diff"
fi

# Check 5: Console/debug statements
DEBUG=$(git diff "$BASE"...HEAD | grep -E '^\+' | grep -vE '^\+\+\+' | grep -iE '(console\.log|debugger|binding\.pry|import pdb|print\()' | head -5 || true)
if [ -n "$DEBUG" ]; then
    echo "$WARN  Possible debug statements added; inspect the diff before publishing"
else
    echo "$PASS  No debug statements detected"
fi

# Check 6: UI files changed (screenshots needed?)
UI_FILES=$(git diff "$BASE"...HEAD --name-only | grep -icE '\.(jsx|tsx|vue|svelte|css|scss|html|erb|astro|mdx)$' || true)
if [ "$UI_FILES" -gt 0 ]; then
    echo "$WARN  $UI_FILES UI-related files changed — include captioned before/after screenshots, or explain why pixels do not change"
else
    echo "$PASS  No UI files changed"
fi

# Check 7: Lint drafted visual evidence when a PR body is supplied
if [ -n "$PR_BODY_FILE" ]; then
    if [ ! -f "$PR_BODY_FILE" ]; then
        echo "$FAIL  PR body file does not exist: $PR_BODY_FILE"
        FAILURES=1
    elif ! command -v python3 >/dev/null 2>&1; then
        echo "$WARN  python3 is unavailable; skipped visual-evidence lint"
    else
        EVIDENCE_ARGS=(--kind "$EVIDENCE_KIND")
        if [ "$EVIDENCE_KIND" = "auto" ] && [ "$UI_FILES" -gt 0 ]; then
            EVIDENCE_ARGS+=(--fallback-kind ui)
        fi
        EXPECTED_BASE=$(git merge-base "$BASE" HEAD)
        EXPECTED_CURRENT=$(git rev-parse HEAD)
        EVIDENCE_ARGS+=(--expected-base-sha "$EXPECTED_BASE" --expected-current-sha "$EXPECTED_CURRENT")
        echo ""
        if python3 "$SCRIPT_DIR/check-visual-evidence.py" "${EVIDENCE_ARGS[@]}" "$PR_BODY_FILE"; then
            echo "$PASS  Visual-evidence lint completed"
        else
            echo "$FAIL  Visual-evidence lint found blocking issues"
            FAILURES=1
        fi
    fi
elif [ "$UI_FILES" -gt 0 ]; then
    echo "$WARN  Pass a PR body file as argument 2 to lint its visual evidence"
fi

echo ""
echo "Done. Address any $WARN warnings and $FAIL failures before submitting."

if [ "$FAILURES" -gt 0 ]; then
    exit 1
fi
