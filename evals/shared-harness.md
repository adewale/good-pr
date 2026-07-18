# Shared benchmark evals

This repo participates in the shared Skill Eval Harness:

- Repo: https://github.com/adewale/skill-eval-harness
- Version: `>=0.6.0`
- Manifest: `evals/shared-benchmark.json`

Install the harness from GitHub with [uv](https://docs.astral.sh/uv/):

```sh
uv tool install git+https://github.com/adewale/skill-eval-harness.git@efe8eba1b20d41e02b81b11015e247b72438cc04
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

`evals/visual-evidence-benchmark.json` freezes the nine-case comparison used by
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

The committed summary records a post-run annotation for the intended source
commit and Git skill tree, and verifies that the installed tree did not change
before the bundle was built. Harness v0.6.0 does not stamp the executed task with
a skill-tree hash, so this is not an execution attestation. The adjacent run CSV
binds every score to an output and artifact-marker hash;
`visual-evidence-gpt-5.4-outputs.jsonl` preserves the sanitized model text and
per-assertion decisions without provider events, traces, or stderr.

Build and verify the proof bundle after running and grading a clean committed
source revision:

```sh
python3 scripts/build_eval_evidence.py build \
  --manifest evals/visual-evidence-benchmark.json \
  --runs eval-runs/visual-evidence-gpt-5.4 \
  --report /tmp/good-pr-visual-evidence-report.json \
  --source-sha <committed-source-sha> \
  --baseline-sha 8e613beba912411217ae89b82fadb081a4380bb5 \
  --baseline-snapshot evals/baselines/good-pr-8e613be \
  --harness-sha efe8eba1b20d41e02b81b11015e247b72438cc04
python3 scripts/build_eval_evidence.py verify \
  evals/results/visual-evidence-gpt-5.4.json
```

Treat visible tune-case statistics as descriptive effect sizes, not as holdout
or confirmatory significance claims. The proof builder deliberately omits
inferential p-values for these tuned cases.

Two sequential replication attempts on pre-fix Harness commit `96013a5`
reproduced the temporary Codex-home cleanup race tracked in
[Skill Eval Harness #45](https://github.com/adewale/skill-eval-harness/issues/45),
aborting after 12 and 29 complete task identities. Those partial runs were
discarded. The recorded final run started from an empty run directory on merged
[PR #46](https://github.com/adewale/skill-eval-harness/pull/46) commit
`efe8eba`; all 81 identities produced complete artifact commits without a
worker abort. The run remained sequential so the only protocol change from the
earlier comparison was the cleanup-race fix.
