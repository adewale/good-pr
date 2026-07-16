# Shared benchmark evals

This repo participates in the shared Skill Eval Harness:

- Repo: https://github.com/adewale/skill-eval-harness
- Version: `>=0.6.0`
- Manifest: `evals/shared-benchmark.json`

Install the harness from GitHub with [uv](https://docs.astral.sh/uv/):

```sh
uv tool install git+https://github.com/adewale/skill-eval-harness.git@96013a50e0139a4886f0fe1cfa932ac5834ce02a
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

The committed summary records the exact evaluated source commit and Git skill
tree. The adjacent run CSV binds every score to an output and artifact-marker
hash; `visual-evidence-gpt-5.4-outputs.jsonl` preserves the sanitized model text
and per-assertion decisions without provider events, traces, or stderr.

Build and verify the proof bundle after running and grading a clean committed
source revision:

```sh
python3 scripts/build_eval_evidence.py build \
  --manifest evals/visual-evidence-benchmark.json \
  --runs eval-runs/visual-evidence-gpt-5.4 \
  --report /tmp/good-pr-visual-evidence-report.json \
  --evaluated-sha <committed-source-sha> \
  --baseline-sha 8e613beba912411217ae89b82fadb081a4380bb5 \
  --baseline-snapshot evals/baselines/good-pr-8e613be \
  --harness-sha 96013a50e0139a4886f0fe1cfa932ac5834ce02a
python3 scripts/build_eval_evidence.py verify \
  evals/results/visual-evidence-gpt-5.4.json
```

Treat visible tune-case statistics as descriptive, not as holdout or
confirmatory significance claims.

The recorded final run used the single sequential `run-codex` command above:
all 81 task identities produced complete Harness commit markers and no cleanup
failure occurred. Parallel runs on the same pinned Harness revision can hit the
temporary Codex-home cleanup race tracked in
[Skill Eval Harness #45](https://github.com/adewale/skill-eval-harness/issues/45);
[PR #46](https://github.com/adewale/skill-eval-harness/pull/46) is the proposed
runner fix. Keeping this frozen comparison sequential isolates the skill change
from that runner defect.
