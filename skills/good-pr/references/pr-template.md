# PR Description Template

Use this template when helping users draft their PR description. Fill in each
section — if a section doesn't apply, remove it rather than writing "N/A".

For a filled-in example showing what "good" looks like, see `pr-example.md`.

---

## What

<!-- One-sentence summary of what this PR does -->

## Why

<!-- Link to the issue this addresses. Brief explanation of the root cause or
motivation. If no issue exists, explain why this change is needed. -->

Fixes #

## How

<!-- What approach you took. If there were alternative approaches, briefly
explain why you chose this one. Keep it concise — the diff tells the detailed
story. -->

## Testing

<!-- What you tested and how. Include:
- Which tests you added or modified
- Whether you verified tests fail when the fix is reverted
- Whether the full test suite passes
- Any manual testing you did -->

- [ ] New/modified tests pass
- [ ] Tests fail when fix is reverted (regression guard)
- [ ] Full test suite passes (no regressions)
- [ ] Manual testing completed (describe below)

## Screenshots / Recordings

<!-- Required for any visual changes. Delete this section entirely if the PR
has no visible impact; if UI files changed without changing pixels, briefly say
why screenshots are not applicable. Caption each before/after pair with the
specific defect it demonstrates, so the reviewer knows what to look at. If the
project renders output programmatically, generate the "before" from an immutable
base commit and the "after" from the immutable head using the same named input,
use full-SHA artifact URLs, and include a regeneration command or hash receipt.
Do not fabricate a before image for a
new/previously unsupported surface; preserve that error baseline honestly. -->

**Before:**

<!-- screenshot or recording -->

**After:**

<!-- screenshot or recording -->

<!-- For generated artifacts, replace the generic Before/After block above with:
Claim: <one visible outcome>
Input/fixture: <same named input and config at both revisions>
Baseline SHA: <immutable base SHA>
Current SHA: <immutable head SHA>
Regenerate: `npm run render-examples`
Independent check: <existing linked test, metric, invariant, or why none is proportionate>
Limitation: <what the image/check cannot prove> -->

<!-- For generated artifacts, prefer:
| Before | After | Why | What to inspect |
Use descriptive alt text, a contact sheet for large matrices, and name the
independent test/metric/freshness gate that supports the screenshot claim. -->

## Risk

<!-- What could go wrong? What shared code does this touch? How did you verify
it's safe? If the risk is minimal, say so and why. -->
