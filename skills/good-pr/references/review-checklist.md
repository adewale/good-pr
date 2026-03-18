# PR Self-Review Checklist

Quick-scan checklist for reviewing a PR before submission. Go through each item
and check it off or note why it doesn't apply.

## Before You Submit

- [ ] **Issue linked** — PR references a specific issue with reproduction steps
- [ ] **Minimal diff** — only changes necessary to solve the stated problem
- [ ] **No drive-by refactors** — no unrelated cleanup, renames, or formatting
- [ ] **Matches project style** — naming, structure, error handling follow
      existing patterns
- [ ] **No new dependencies** — or dependency addition was discussed first

## Testing

- [ ] **Tests added** — new or modified tests cover the change
- [ ] **Regression guard verified** — tests fail when the fix is reverted
- [ ] **Full suite passes** — ran the complete test suite, not just new tests
- [ ] **Edge cases covered** — empty inputs, error states, boundary conditions

## Visual Changes (if applicable)

- [ ] **Before/after included** — screenshots or recordings in PR description
- [ ] **Multiple states shown** — empty, loading, error, populated
- [ ] **Responsive checked** — different viewport sizes if relevant

## Description Quality

- [ ] **What** — clear one-sentence summary
- [ ] **Why** — root cause or motivation explained
- [ ] **How** — approach described, alternatives noted if relevant
- [ ] **Testing** — test strategy and verification steps documented
- [ ] **Risk** — potential impact areas identified and mitigated

## Final Check

- [ ] **Read your own diff** — review every line as if you were the maintainer
- [ ] **PR title is descriptive** — someone scanning a PR list can understand it
- [ ] **No secrets or credentials** — .env files, API keys, tokens not included
