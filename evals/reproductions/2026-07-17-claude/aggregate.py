#!/usr/bin/env python3
"""Aggregate graded visual-evidence eval runs into the PR's table shape.

Mirrors scripts/build_eval_evidence.py aggregate + compare_variants math, but
does not enforce the skill-invocation proof gate (the claude backend injects
skill content inline, so trace-based skill_invoked is not observable here).
"""
import csv
import itertools
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

VARIANTS = ("without_skill", "old_skill", "with_skill")
GRADE = Path(sys.argv[1])
RUNS = Path(sys.argv[2])


def mean(v):
    return round(sum(v) / len(v), 10) if v else 0.0


report = json.loads(GRADE.read_text())
results = report["results"]

# attach metadata (elapsed/tokens) per run
for r in results:
    md = RUNS / r["case_id"] / r["variant"] / f"run-{r['run_number']}" / "metadata.json"
    m = json.loads(md.read_text()) if md.is_file() else {}
    r["_elapsed_ms"] = m.get("elapsed_ms")
    r["_total_tokens"] = m.get("total_tokens")
    r["_cost"] = m.get("cost_usd")

by_variant = defaultdict(list)
by_case_variant = defaultdict(list)
for r in results:
    by_variant[r["variant"]].append(r)
    by_case_variant[(r["case_id"], r["variant"])].append(r)

aggregate = {}
for variant in VARIANTS:
    rows = by_variant[variant]
    if not rows:
        continue
    cases = sorted({r["case_id"] for r in rows})
    pass_at_1, all_runs, case_rates = [], [], {}
    for c in cases:
        cr = by_case_variant[(c, variant)]
        complete = [r["objective_passed"] == r["objective_total"] for r in cr]
        pass_at_1.append(sum(complete) / len(complete))
        all_runs.append(all(complete))
        case_rates[c] = mean([r["objective_pass_rate"] for r in cr])
    aggregate[variant] = {
        "objective_pass_rate": mean([r["objective_pass_rate"] for r in rows]),
        "mean_pass_at_1": mean(pass_at_1),
        "all_runs_pass_rate": mean([float(x) for x in all_runs]),
        "median_elapsed_ms": statistics.median([r["_elapsed_ms"] for r in rows if r["_elapsed_ms"] is not None]) if any(r["_elapsed_ms"] is not None for r in rows) else None,
        "median_total_tokens": statistics.median([r["_total_tokens"] for r in rows if r["_total_tokens"] is not None]) if any(r["_total_tokens"] is not None for r in rows) else None,
        "n_runs": len(rows),
        "case_objective_pass_rate": case_rates,
    }


def compare(cand, ref):
    cc = aggregate[cand]["case_objective_pass_rate"]
    rc = aggregate[ref]["case_objective_pass_rate"]
    deltas = {c: round(cc[c] - rc[c], 10) for c in sorted(cc)}
    observed = abs(mean(list(deltas.values())))
    perms = [abs(mean([s * d for s, d in zip(signs, deltas.values())]))
             for signs in itertools.product((-1, 1), repeat=len(deltas))]
    p = sum(v >= observed - 1e-12 for v in perms) / len(perms)
    return {
        "candidate": cand, "reference": ref,
        "absolute_delta": round(aggregate[cand]["objective_pass_rate"] - aggregate[ref]["objective_pass_rate"], 10),
        "negative_delta_cases": [c for c, d in deltas.items() if d < 0],
        "observed_mean_delta": round(observed, 10),
        "p_value": round(p, 10),
        "significant_at_0_05": p < 0.05,
        "case_delta": deltas,
    }


def pct(x):
    return f"{x*100:.2f}%"


print("=" * 78)
print("VISUAL-EVIDENCE EVAL — model: claude (Opus 4.8 default backend)")
print(f"graded results: {len(results)}  (expected 81)")
print("=" * 78)
hdr = f"{'Variant':16}{'ObjPass':>9}{'pass@1':>9}{'allruns':>9}{'medElapsed':>12}{'medTokens':>11}{'n':>4}"
print(hdr)
for v in VARIANTS:
    if v not in aggregate:
        continue
    a = aggregate[v]
    me = f"{a['median_elapsed_ms']/1000:.1f}s" if a["median_elapsed_ms"] else "-"
    mt = f"{int(a['median_total_tokens'])}" if a["median_total_tokens"] else "-"
    print(f"{v:16}{pct(a['objective_pass_rate']):>9}{pct(a['mean_pass_at_1']):>9}{pct(a['all_runs_pass_rate']):>9}{me:>12}{mt:>11}{a['n_runs']:>4}")

print("-" * 78)
for cand, ref in [("with_skill", "without_skill"), ("with_skill", "old_skill")]:
    if cand in aggregate and ref in aggregate:
        cmp = compare(cand, ref)
        print(f"{cand} vs {ref}: +{pct(cmp['absolute_delta'])} obj  "
              f"p={cmp['p_value']} sig={cmp['significant_at_0_05']}  "
              f"neg_cases={cmp['negative_delta_cases']}")

out = {"aggregate": aggregate,
       "with_skill_vs_without_skill": compare("with_skill", "without_skill") if "with_skill" in aggregate and "without_skill" in aggregate else None,
       "with_skill_vs_old_skill": compare("with_skill", "old_skill") if "with_skill" in aggregate and "old_skill" in aggregate else None}
Path(sys.argv[3]).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
print(f"\nwrote {sys.argv[3]}")
