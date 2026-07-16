# Visual Evidence That Reviewers Can Trust

Use this reference for PRs that change application UI, diagrams, charts, PDFs,
images, generated documentation, or any other output reviewers must see.

## Contents

- Evidence policy by change type
- Generated-output proof contract
- GitHub attachment difficulties
- Lessons from the authored-PR corpus
- Automated audit

## Evidence policy by change type

| Change type | Proportionate evidence |
|---|---|
| Ordinary UI | Hand-taken before/after screenshots or a recording, with useful captions and relevant states/viewports |
| Programmatically generated output | Same named input/config rendered at immutable base and head commits, SHA-pinned artifacts, a regeneration command or hash receipt, an existing oracle when machine-checkable, and a material limitation |
| New or previously unsupported surface | Honest error/unsupported baseline plus after evidence; do not fabricate a before image |
| No visible impact | A short, concrete explanation of why screenshots are not applicable, followed by the non-visual evidence that does apply |

## Generated-output proof contract

Use this compact contract for generated, high-risk, or mechanically verifiable
visual claims. Keep ordinary UI screenshots lightweight.

```markdown
## Visual evidence

Claim: `<one visible outcome the images demonstrate>`

Input/fixture: `<checked-in path or stable identifier>; same config at both revisions`

Baseline SHA: `<full or identified immutable SHA>`

Current SHA: `<full head SHA>`

Regenerate: `npm run render-pr-evidence`

| Before | After | Why | What to inspect |
|---|---|---|---|
| <img alt="Before: label overlaps the container border" src="<SHA-pinned URL>" width="380"> | <img alt="After: label clears the container border" src="<SHA-pinned URL>" width="380"> | The old anchor used the label centre instead of its edge. | The label clears the border in all four directions; the unchanged arrow is a control. |

Independent check: [`tests/label-geometry.test.ts`](<commit-pinned URL>) asserts label-to-border clearance.

Limitation: This fixture checks one font stack and viewport; the image does not prove every label layout or general readability.
```

`Receipt: evidence/receipt.json` may replace `Regenerate:` when it records the
generator/version, input hash, base/head SHAs, output hashes, and check result.
One combined contact sheet is fine; lead with the failing row or crop that drives
the decision and link exhaustive evidence. A new surface may have only an after
image if the description preserves the real unsupported/error baseline.

Reuse the production renderer, existing fixtures, and existing tests. Do not
create parallel rendering logic or a proof-only approval system unless its
maintenance cost is justified by recurring risk. For subjective claims, use the
same-input comparison and an honest limitation instead of inventing a metric.

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
- **Commented, fenced, indented, or inline examples are not evidence.** Template
  placeholders and code samples do not render as screenshots and are ignored.
- **A screenshot cannot prove its own correctness.** Back perceptual claims with
  tests, measurements, controls, or freshness gates when those claims are
  mechanically expressible.

## Lessons from an authored-PR corpus

On 2026-07-16, a public-repository GitHub search over all 629 PRs authored by
`adewale` found 598 PRs in `adewale/*` repositories and 31 external
contributions across 51 repositories. This scan excludes image-like syntax
inside HTML comments, fenced
examples, indented code, and inline code; it does not judge pixels. The versioned
corpus receipt preserves URLs, observation times, body hashes, and extracted
features without copying PR bodies. Counts will drift as descriptions change;
the receipt cannot reconstruct later edits.

- 49 PRs embedded 208 rendered images or image tags.
- 44/49 image-bearing PRs discussed before and after; 41/49 discussed
  regeneration or reproduction.
- Only 29/49 used at least one SHA-pinned repository image. The corpus still
  contained 51 repository image URLs or relative paths with mutable refs.
- 79 image embeds had missing or very short alt text.
- Only 11 image-bearing PRs explicitly told reviewers what to inspect, and
  ten used contact sheets.
- Eleven PRs gave an explicit reason screenshots were not applicable.
- Two PR descriptions contained doubled-backtick image URLs that may not render.

Representative lessons:

- [`agentic-mermaid#183`](https://github.com/adewale/agentic-mermaid/pull/183)
  states exactly what its focused editor image cannot prove and routes the
  nonvisual API/transport claims to source ratchets and negative tests.
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

## Mechanical lint

Run:

```bash
python3 <good-pr-skill-dir>/scripts/check-visual-evidence.py --kind ui pr-body.md
python3 <good-pr-skill-dir>/scripts/check-visual-evidence.py --kind generated --strict pr-body.md
```

The linter validates mechanical properties only: section/media presence,
alt/link-text presence, immutable repository refs, generated base/head labels,
and malformed URLs. The readiness wrapper accepts an
explicit third argument (`ui`, `generated`, or `none`) and supplies the actual
merge-base/head SHAs. Direct generated mode checks only that SHA-like labels are
present. The linter does not fetch assets or decide whether the claim, input,
reproduction path, independent check, limitation, or pixels are valid. Review
those semantic parts with the compact proof contract above.
