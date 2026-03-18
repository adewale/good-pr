# Concrete PR Example

A filled-in PR description showing what "good" looks like. Use this as a
reference when helping users — it's easier to adapt a real example than fill
in a blank template.

---

## What

Fix crash when submitting the settings form with no changes.

## Why

Fixes #247.

The settings form throws a 500 error when a user clicks "Save" without
modifying any fields. Root cause: `updateSettings()` sends a PATCH request
with an empty body, and the API returns a validation error that the frontend
doesn't handle.

This affects every user who opens settings and clicks save — the error rate
in Sentry shows ~300 occurrences/day since the 2.4.0 release.

## How

Added an early return in `handleSubmit()` that checks whether any fields
have changed before making the API call. If nothing changed, the form shows
a "No changes to save" toast instead.

**Alternatives considered:**
- Making the API accept empty PATCH bodies — rejected because the API
  validation is correct (other clients depend on it), and the fix belongs
  in the frontend
- Disabling the save button when nothing changed — rejected because it
  removes the ability to "re-save" and changes established UX patterns

## Testing

- Added unit test for empty-form submission in `settings.test.ts`
- **Verified test fails when the guard clause on line 42 is removed**
- Existing test suite passes: `npm test` — 247 passed, 0 failed
- Manual testing: opened settings, clicked save with no changes, confirmed
  toast appears and no network request is made

## Screenshots / Recordings

**Before:**

![500 error on empty save](before-500-error.png)

**After:**

![No changes toast on empty save](after-toast.png)

## Risk

Low. The change is a single guard clause at the top of `handleSubmit()`. It
only affects the empty-change path — all other save flows are untouched. The
existing test suite covers normal save operations and still passes.

---

## Why This Example Works

Note what makes this effective:

1. **One-sentence "What"** — the maintainer knows immediately what this does
2. **"Why" links to an issue AND explains root cause** — not just "it was broken"
3. **Quantified impact** — 300 errors/day gives the maintainer priority context
4. **"How" explains alternatives** — shows the contributor thought it through
5. **Testing proves the fix** — the regression guard line is the key credibility signal
6. **Risk is honest and scoped** — "low, here's why" is more trustworthy than no risk section
