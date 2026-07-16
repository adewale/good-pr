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
- [ ] **Each pair captioned** — text states the specific defect or change the
      images demonstrate
- [ ] **Evidence is reproducible** — if the project renders output
      programmatically, the same named input/config is generated at immutable
      base and head commits and a regeneration command or receipt is noted
- [ ] **Claim precedes evidence** — one visible claim appears before each
      generated comparison
- [ ] **URLs are immutable** — generated repository assets use full commit-SHA
      URLs rather than branches or relative paths
- [ ] **Review cue included** — captions say why the pixels changed and exactly
      what the reviewer should inspect
- [ ] **Alt text is descriptive** — every Markdown or HTML image describes the
      visible claim
- [ ] **Evidence is proportional** — large matrices use a contact sheet plus
      links; new/unsupported surfaces preserve the honest error baseline rather
      than fabricating a before image
- [ ] **Independent oracle named** — machine-checkable visual claims also have
      an existing linked test, metric, control, or freshness gate; subjective
      claims do not invent a misleading metric
- [ ] **Limitation stated** — generated evidence says what fixture, state,
      environment, or quality dimension it cannot prove
- [ ] **No proof-only codebase** — evidence reuses production rendering,
      checked-in fixtures, and existing checks unless recurring risk justifies more
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
