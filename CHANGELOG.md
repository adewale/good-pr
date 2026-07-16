# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Dependency-free `check-visual-evidence.py` audit for PR Markdown, with
  proportionate ordinary-UI/generated-output policies, immutable GitHub URL
  checks, honest no-baseline handling, accessibility/reviewer cues, malformed
  image detection, contact-sheet guidance, JSON output, and strict mode
- Corpus-derived visual-evidence reference based on 629 authored PRs across 51
  repositories, including durable examples and observed GitHub attachment
  failure modes
- Re-runnable `analyze_pr_visual_evidence.py` GitHub corpus scanner used to
  reproduce the aggregate evidence metrics and exemplar ranking
- Versioned row-level corpus receipt with observation timestamps, PR/body
  hashes, and extracted features while omitting PR body text
- Nine visual-evidence benchmark cases covering durable generated artifacts,
  honest missing baselines, no-visible-impact restraint, malformed Markdown,
  independent correctness oracles, the full proof contract, and restraint for
  subjective evidence
- Reproducible nine-case, three-arm visual-evidence comparison with a committed
  baseline skill snapshot, model-pinned manifest, compact result, provenance
  hashes, sanitized row-level outputs, and exact rerun commands
- Sanitized output/per-assertion eval proof bundle, source/tree binding, and a
  CI verifier for the manifest, run matrix, outputs, and frozen baseline
- Compact generated-output proof contract covering a named claim and input,
  immutable base/head, reproduction or receipt, associated existing oracle,
  material limitation, and proportional reuse of production fixtures

- Visual evidence provenance guidance (inspired by beautiful-mermaid PR #22):
  caption each before/after pair with the specific defect it demonstrates,
  prefer generated artifacts rendered from base commit vs. branch when the
  project renders output programmatically, and include the regeneration
  command — in `SKILL.md` section 2, `pr-template.md`, and
  `review-checklist.md`
- Benchmark tune case `pos-renderer-evidence-provenance` and ablation
  `no-evidence-provenance` in `evals/shared-benchmark.json`

### Fixed

- Visual evidence audits now ignore commented/fenced placeholders, recognize
  GitHub recording attachments, bind causal comparisons to sufficient media,
  require an explicitly labelled baseline commit, and distinguish application
  UI from generated rendered output
- Readiness failures now return a non-zero exit status, while auto-detection can
  use UI-file changes as a fallback without downgrading generated-output policy
- Corpus analysis excludes non-rendered examples and counts relative repository
  image paths as mutable evidence
- Visual audits now ignore unclosed comments and indented code, support
  reference-style images, bind labelled proof fields to the visual section and
  checked-out revisions, distinguish external URL provenance, and reject
  contradictory no-impact claims
- Readiness checks accept an explicit evidence kind, recognize generated/binary
  changes, and keep lexical secret detection advisory and redacted
- Eval negation guards no longer reject “no need” answers, code-formatted `alt`
  guidance is recognized, benchmark and ablation skill paths resolve from the
  manifest directory, and regression tests run in CI

## [0.1.0] - 2026-03-13

### Added

- Core skill (`good-pr/SKILL.md`) with 7-point checklist covering reproduction steps, visual evidence, code fit, meaningful tests, scoped changes, standalone descriptions, and contributor trust
- PR description template (`good-pr/references/pr-template.md`)
- Self-review checklist (`good-pr/references/review-checklist.md`)
- Automated PR readiness check script (`good-pr/scripts/check-pr-readiness.sh`) — checks diff size, test file presence, secrets, debug statements, and UI file changes
- Eval test cases for skill validation (`evals/evals.json`)
- README crediting [@lukeparkerdev's tweet](https://x.com/lukeparkerdev/status/2032300518010470555) as the inspiration

[0.1.0]: https://github.com/adewale/good-pr/releases/tag/v0.1.0
