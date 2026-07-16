# Shared benchmark evals

This repo participates in the shared Skill Eval Harness:

- Repo: https://github.com/adewale/skill-eval-harness
- Version: `>=0.6.0`
- Manifest: `evals/shared-benchmark.json`

Install the harness from GitHub with [uv](https://docs.astral.sh/uv/):

```sh
uv tool install git+https://github.com/adewale/skill-eval-harness.git@v0.6.0
```

Splits:
- `tune` — visible iteration cases.
- `holdout` — hidden end-of-round / merge scoring cases.
- `holdback` — examples withheld from `SKILL.md`, references, docs, and public eval descriptions until after scoring.

Validate from this repo root:

```sh
skill-benchmark validate evals/shared-benchmark.json
```

Prepare paired run tasks:

```sh
skill-benchmark prepare evals/shared-benchmark.json --split tune --out /tmp/good-pr-tasks.jsonl
```

Include ablation variants when running a focused regression check:

```sh
skill-benchmark prepare evals/shared-benchmark.json --split tune --include-ablations --out /tmp/good-pr-ablation-tasks.jsonl
```

Run autonomous Pi trigger checks for trigger/no-trigger cases:

```sh
skill-pi-trigger-eval evals/shared-benchmark.json --split tune --out /tmp/good-pr-trigger-report.json
```

`old_skill` is optional and intentionally not emitted unless `old_skill_paths` is populated and `--include-old-skill` is passed. Hidden `holdout` / `holdback` prompt refs must be supplied privately before scoring; use `--allow-missing-prompts` only for dry-run planning.

Grade saved outputs:

```sh
skill-benchmark benchmark evals/shared-benchmark.json --runs eval-runs/latest --allow-scripts --out /tmp/good-pr-benchmark.json
```

Run optional qualitative judges through the shared `judge` backend:

```sh
skill-benchmark judge evals/shared-benchmark.json --runs eval-runs/latest --judge-cmd 'claude -p' --transcripts eval-runs/judge-transcripts --out /tmp/good-pr-judge-results.jsonl
skill-benchmark benchmark evals/shared-benchmark.json --runs eval-runs/latest --allow-scripts --judge-results /tmp/good-pr-judge-results.jsonl --out /tmp/good-pr-benchmark.json
```

Script assertions are deterministic repo-owned oracles and require `--allow-scripts` during grading.

## Reproduce the visual-evidence comparison

`evals/visual-evidence-benchmark.json` freezes the seven-case comparison used by
PR #11. Its `old_skill` arm points to the committed snapshot of `good-pr` at
`8e613beba912411217ae89b82fadb081a4380bb5`; no sibling checkout or temporary
manifest edit is required.

The recorded comparison uses `gpt-5.4` explicitly and low reasoning effort:

```sh
skill-benchmark validate evals/visual-evidence-benchmark.json --strict-leakage
skill-benchmark prepare evals/visual-evidence-benchmark.json \
  --split tune --runs-per-variant 3 --models gpt-5.4 \
  --out /tmp/good-pr-visual-evidence-tasks.jsonl
skill-benchmark run-codex \
  --tasks /tmp/good-pr-visual-evidence-tasks.jsonl \
  --runs eval-runs/visual-evidence-gpt-5.4 \
  --codex-cmd "codex exec --json -c model_reasoning_effort=low" \
  --timeout 600
skill-benchmark benchmark evals/visual-evidence-benchmark.json \
  --runs eval-runs/visual-evidence-gpt-5.4 \
  --out /tmp/good-pr-visual-evidence-report.json
```

The committed result at `evals/results/visual-evidence-gpt-5.4.json` records the
model, harness/baseline revisions, content-tree and artifact-inventory hashes,
case-level scores, diagnostic grader rounds, run counts, medians, and exact
commands. The adjacent `visual-evidence-gpt-5.4-runs.csv` preserves all 63
run-level objective scores and execution/provenance fields. Raw model transcripts
remain uncommitted because they are large and
may contain provider metadata; the frozen manifest and commands are the
reproduction path. Treat visible tune-case p-values as descriptive, not as
holdout or confirmatory significance claims.

The recorded final run attempted parallel partitions, and three workers aborted
after successful invocations when temporary Codex-home cleanup encountered
lingering plugin-clone paths. Only artifact sets with Harness commit markers
were counted; missing task identities were rerun sequentially. The single
`run-codex` command above is sequential and avoids that observed concurrency
failure mode.
