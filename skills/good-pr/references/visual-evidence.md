# Visual Evidence That Reviewers Can Trust

Use this reference for PRs that change application UI, diagrams, charts, PDFs,
images, generated documentation, or any other output reviewers must see.

## Evidence policy by change type

| Change type | Proportionate evidence |
|---|---|
| Ordinary UI | Hand-taken before/after screenshots or a recording, with useful captions and relevant states/viewports |
| Programmatically generated output | Same input rendered at an immutable base commit and at the proposed head, SHA-pinned artifacts, exact regeneration command, and an independent oracle |
| New or previously unsupported surface | Honest error/unsupported baseline plus after evidence; do not fabricate a before image |
| No visible impact | A short, concrete explanation of why screenshots are not applicable, followed by the non-visual evidence that does apply |

## Recommended generated-evidence shape

```markdown
## Visual evidence

Baseline: `<full or identified immutable SHA>`

Current: `<head SHA>`

Regenerate: `npm run render-pr-evidence`

| Before | After | Why | What to inspect |
|---|---|---|---|
| <img alt="Before: label overlaps the container border" src="<SHA-pinned URL>" width="380"> | <img alt="After: label clears the container border" src="<SHA-pinned URL>" width="380"> | The old anchor used the label centre instead of its edge. | The label clears the border in all four directions; the unchanged arrow is a control. |

Independent checks:
- geometry assertion for label-to-border clearance
- evidence freshness check over inputs and image bytes
```

One combined before/after contact sheet is fine. A new surface may have only an
after image if the description preserves the real unsupported/error baseline.

## GitHub attachment difficulties

- **Branch URLs are mutable.** A URL under
  `raw.githubusercontent.com/<owner>/<repo>/<branch>/...` can change after the
  PR is reviewed and can break after branch deletion. For generated evidence,
  use the full 40-character commit SHA in the URL.
- **Uploaded attachments prove pixels, not provenance.** GitHub-hosted user
  attachments are convenient for ordinary UI screenshots. For generated output,
  commit the artifact when practical so the URL, generator, inputs, and source
  revision can be reviewed together.
- **HTML sizing trades convenience for accessibility risk.** `<img width>`
  keeps comparison tables readable, but always add meaningful `alt` text.
- **Large matrices overwhelm the PR conversation.** Prefer one overview/contact
  sheet and one focused crop; link exhaustive permutations rather than embedding
  dozens of full-size images.
- **Markdown mistakes can silently erase evidence.** Preview the PR description.
  In particular, do not wrap an image URL in doubled backticks.
- **Uploaded recordings are bare attachment URLs.** Give them descriptive link
  text or a nearby caption so reviewers know the interaction and states shown.
- **Commented or fenced examples are not evidence.** Template placeholders and
  code samples do not render as screenshots and are ignored by the audit.
- **A screenshot cannot prove its own correctness.** Back perceptual claims with
  tests, measurements, controls, or freshness gates when those claims are
  mechanically expressible.

## Lessons from an authored-PR corpus

On 2026-07-16, a GitHub search over all 627 PRs authored by `adewale` found 596
PRs in `adewale/*` repositories and 31 external contributions across 52
repositories. This scan excludes image-like syntax inside HTML comments, fenced
examples, and inline code; it does not judge pixels. Counts will drift as PR
descriptions change.

- 47 PRs embedded 198 rendered images or image tags.
- 42/47 image-bearing PRs discussed before and after; 39/47 discussed
  regeneration or reproduction.
- Only 27/47 used at least one SHA-pinned repository image. The corpus still
  contained 51 repository image URLs or relative paths with mutable refs.
- 71 image embeds had missing or very short alt text.
- Only nine image-bearing PRs explicitly told reviewers what to inspect, and
  nine used contact sheets.
- Ten PRs gave an explicit reason screenshots were not applicable.
- Two PR descriptions contained doubled-backtick image URLs that may not render.

Representative lessons:

- [`agentic-mermaid#180`](https://github.com/adewale/agentic-mermaid/pull/180)
  is the compact target: exact causal source, SHA-pinned before/after, descriptive
  alt text, `Why`, `What to inspect`, focused crops, and independent geometry
  assertions.
- [`agentic-mermaid#176`](https://github.com/adewale/agentic-mermaid/pull/176)
  overlays measured gaps and makes the evidence generator fail when the old bug
  stops reproducing or the new threshold regresses.
- [`agentic-mermaid#172`](https://github.com/adewale/agentic-mermaid/pull/172)
  uses contact sheets and hash-bound approval, and refuses to manufacture a
  visual baseline for a capability the old version could not render.
- [`agentic-mermaid#149`](https://github.com/adewale/agentic-mermaid/pull/149)
  shows the cost of exhaustive inline proof: 30 embedded images make coverage
  strong but scanning expensive, and most HTML images lack alt text.
- [`agentic-mermaid#94`](https://github.com/adewale/agentic-mermaid/pull/94)
  explains that page geometry did not change and substitutes endpoint/test
  evidence instead of padding the PR with irrelevant screenshots.
- [`agentic-mermaid#22`](https://github.com/adewale/agentic-mermaid/pull/22)
  introduced reproducible worktree-rendered evidence, but also demonstrates how
  a doubled-backtick URL can undermine an otherwise strong screenshot section.
- Early examples such as
  [`agentic-mermaid#3`](https://github.com/adewale/agentic-mermaid/pull/3)
  use branch-linked representative renders; later PRs show the evolution toward
  immutable, causal evidence packages.

The broad PR-quality lesson is the same as the visual one: make claims
reviewable. Strong descriptions repeatedly combine a standalone `What/Why/How`,
reproduction, discriminating tests that fail on the old behavior, bounded risk,
measured outcomes, and honest residual limitations. Examples include
[`good-pr#9`](https://github.com/adewale/good-pr/pull/9) for ablation-backed skill
guidance, [`skill-eval-harness#24`](https://github.com/adewale/skill-eval-harness/pull/24)
for measurable eval infrastructure, and
[`geist_fabrik#80`](https://github.com/adewale/geist_fabrik/pull/80) for a
multi-defect release-quality pass with regression proof.

## Automated audit

Run:

```bash
python3 <good-pr-skill-dir>/scripts/check-visual-evidence.py --kind ui pr-body.md
python3 <good-pr-skill-dir>/scripts/check-visual-evidence.py --kind generated --strict pr-body.md
```

The checker validates Markdown-level evidence contracts: section presence,
causal before/after or honest baseline absence, descriptive alt text, immutable
GitHub repository refs, regeneration commands, review cues, malformed URLs, and
excessive inline volume. Generated-output audits also warn when no independent
test, metric, control, or freshness check is named. It intentionally does not
fetch assets or decide whether the pixels look correct.
