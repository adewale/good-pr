# PR #11 eval — reproduction across Claude models (Haiku 4.5, Sonnet 5, Opus 4.8)

**PR:** adewale/good-pr#11 — *Teach durable visual evidence and add mechanical PR lint*
**Source evaluated:** PR head `f032eeb` (skill under test) vs baseline `8e613be`
**Harness:** skill-eval-harness `v0.6.0`
**Manifest:** `evals/visual-evidence-benchmark.json` — 9 tune cases × 3 variants × 3 reps = **81 runs per model**
**Models:** `claude-haiku-4-5-20251001`, `claude-sonnet-5`, `claude-opus-4-8` via the harness `claude`
backend. The PR's frozen run used `gpt-5.4`, which is unavailable in this environment; its numbers are
quoted from the committed proof bundle for reference. Everything else (manifest, variants, splits, reps)
matches the PR.
**Execution integrity:** 81/81 outputs per model, 0 execution errors, 0 missing.
Cost: Haiku ≈ $2.33, Sonnet ≈ $12.62, Opus ≈ $11.45.

## Objective pass rate by model and variant

| Model | no-skill | baseline `8e613be` | **new skill** | new−baseline | p(base) | new−no-skill | p(none) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gpt-5.4 (PR frozen) | 52.2% | 63.0% | **90.4%** | +27.5% | 0.0156 | +38.3% | 0.0039 |
| claude-opus-4-8 | 44.4% | 63.6% | **88.6%** | +25.0% | 0.0625 | +44.1% | 0.0078 |
| claude-sonnet-5 | 47.8% | 62.3% | **89.8%** | +27.5% | 0.0469 | +42.0% | 0.0156 |
| claude-haiku-4-5 | 52.2% | 60.8% | **87.7%** | +26.9% | 0.0313 | +35.5% | 0.0156 |

p-values are the manifest's own case-mean sign-flip exact test (n=9).

### pass@1 and all-runs-pass (new skill)

| Model | pass@1 | all-runs-pass |
|---|---:|---:|
| gpt-5.4 (PR frozen) | 70.4% | 55.6% |
| claude-opus-4-8 | 74.1% | 55.6% |
| claude-sonnet-5 | 70.4% | 55.6% |
| claude-haiku-4-5 | 66.7% | 55.6% |

## What this shows

The PR's central finding is **model-robust**. On every model — from the smallest (Haiku) to the
largest (Opus), and matching the PR's gpt-5.4 — the new skill lands at **87.7–90.4%** objective pass,
the frozen baseline at **60.8–63.6%**, and no-skill at **44.4–52.2%**. The skill lift over the baseline
is **+25.0 to +27.5 points** everywhere, and every model reaches exactly **55.6% all-runs-pass** (5/9
cases passing all three reps).

- **new vs no-skill** is significant on all four models (p ≤ 0.0156).
- **new vs baseline** is significant on Haiku (0.0313), Sonnet (0.0469), and gpt-5.4 (0.0156); on Opus it
  is marginal (0.0625) because one negative case flips. With only 3 reps the sign-flip test is coarse, so
  a single case swing moves it across 0.05.

### Negative-case regressions vs baseline (where the new skill occasionally over-asks)

| Model | negative-delta case(s) vs baseline |
|---|---|
| gpt-5.4 | none |
| claude-opus-4-8 | neg-ordinary-ui-no-artifact-demand |
| claude-sonnet-5 | neg-ordinary-ui-no-artifact-demand |
| claude-haiku-4-5 | none |

The recurring one, `neg-ordinary-ui-no-artifact-demand`, is an ordinary UI change that should *not*
trigger heavy generated-evidence demands; the new skill sometimes over-asks there. It is the single case
keeping Opus's new-vs-baseline test marginal.

## Deterministic checks from the PR's "Testing" section (all reproduced green)

| Check | Result |
|---|---|
| `build_eval_evidence.py verify visual-evidence-gpt-5.4.json` | OK — 81 committed gpt-5.4 outputs verified |
| `python3 -m unittest discover -s tests` | 34/34 OK |
| `check_install_boundary.py` | clean |
| `bash -n check-pr-readiness.sh` | syntax OK |
| `git diff --check` | clean |
| focused / shared strict-leakage validate | OK — 9 cases; 29 cases, 6 ablations |

## Files

- `<model>/aggregate.json` — machine-readable aggregate + sign-flip comparisons per model. These are the
  committed receipt.
- `aggregate.py` — aggregator (mirrors `scripts/build_eval_evidence.py` math; skips the trace-based
  skill-invocation proof gate, since the claude backend injects skill content inline).
- `run_model.sh` — single-task runner: `MODEL RUNS_DIR TASK_FILE`, fanned out 6–8 way with `xargs -P`.

Raw per-run model outputs and the per-run score matrices are **not** committed (bulk, low-signal); they
are regenerable from the commands below, and the per-model `aggregate.json` carries every number in this
report.

## How to reproduce (one model)

```sh
uv tool install git+https://github.com/adewale/skill-eval-harness.git@v0.6.0
git checkout f032eeb
skill-benchmark prepare evals/visual-evidence-benchmark.json \
  --split tune --runs-per-variant 3 --out /tmp/ve-tasks.jsonl   # omit --include-old-skill (double-emits)
# split /tmp/ve-tasks.jsonl into one task file per line, then fan out:
#   ls tasks/*.jsonl | xargs -P 8 -I{} ./run_model.sh claude-sonnet-5 /tmp/runs {}
skill-benchmark grade evals/visual-evidence-benchmark.json --runs /tmp/runs --allow-scripts --out grade.json
python3 aggregate.py grade.json /tmp/runs aggregate.json
```
