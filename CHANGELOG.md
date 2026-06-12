# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Visual evidence provenance guidance (inspired by beautiful-mermaid PR #22):
  caption each before/after pair with the specific defect it demonstrates,
  prefer generated artifacts rendered from base commit vs. branch when the
  project renders output programmatically, and include the regeneration
  command — in `SKILL.md` section 2, `pr-template.md`, and
  `review-checklist.md`
- Benchmark tune case `pos-renderer-evidence-provenance` and ablation
  `no-evidence-provenance` in `evals/shared-benchmark.json`

## [0.1.0] - 2026-03-13

### Added

- Core skill (`good-pr/SKILL.md`) with 7-point checklist covering reproduction steps, visual evidence, code fit, meaningful tests, scoped changes, standalone descriptions, and contributor trust
- PR description template (`good-pr/references/pr-template.md`)
- Self-review checklist (`good-pr/references/review-checklist.md`)
- Automated PR readiness check script (`good-pr/scripts/check-pr-readiness.sh`) — checks diff size, test file presence, secrets, debug statements, and UI file changes
- Eval test cases for skill validation (`evals/evals.json`)
- README crediting [@lukeparkerdev's tweet](https://x.com/lukeparkerdev/status/2032300518010470555) as the inspiration

[0.1.0]: https://github.com/adewale/good-pr/releases/tag/v0.1.0
