#!/usr/bin/env python3
"""Build or verify a compact, auditable Skill Eval Harness proof bundle."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ("with_skill", "old_skill", "without_skill")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def hash_tree(path: Path) -> str:
    """Hash relative paths, executable modes, and bytes with a documented format."""
    digest = hashlib.sha256()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        relative = item.relative_to(path).as_posix()
        mode = "100755" if item.stat().st_mode & 0o111 else "100644"
        digest.update(f"{mode} {relative}\0".encode())
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def identity(record: dict) -> tuple[str, str, int]:
    return record["case_id"], record["variant"], int(record["run_number"])


def mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 10) if values else 0.0


def build(args: argparse.Namespace) -> int:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = json.loads(args.report.read_text(encoding="utf-8"))
    results = sorted(report["results"], key=identity)
    expected = len(manifest["cases"]) * len(VARIANTS) * args.runs_per_variant
    if len(results) != expected:
        raise SystemExit(f"expected {expected} graded results, found {len(results)}")

    proof_records: list[dict] = []
    csv_rows: list[dict] = []
    seen: set[tuple[str, str, int]] = set()
    for result in results:
        key = identity(result)
        if key in seen:
            raise SystemExit(f"duplicate result identity: {key}")
        seen.add(key)
        case_id, variant, run_number = key
        run_dir = args.runs / case_id / variant / f"run-{run_number}"
        output_path = run_dir / "output.md"
        commit_path = run_dir / "artifact-commit.json"
        metadata_path = run_dir / "metadata.json"
        for required in (output_path, commit_path, metadata_path):
            if not required.is_file():
                raise SystemExit(f"missing committed run artifact: {required}")
        output = output_path.read_text(encoding="utf-8")
        commit = json.loads(commit_path.read_text(encoding="utf-8"))
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        output_hash = sha256_bytes(output.encode())
        if commit.get("inventory_sha256", {}).get("output.md") != output_hash:
            raise SystemExit(f"artifact inventory mismatch: {output_path}")
        commit_hash = sha256_file(commit_path)
        assertions = [
            {
                key: assertion.get(key)
                for key in ("name", "type", "passed", "evidence", "severity", "oracle")
            }
            for assertion in result.get("assertions", [])
        ]
        record = {
            "case_id": case_id,
            "variant": variant,
            "run_number": run_number,
            "model": result.get("model"),
            "output_sha256": output_hash,
            "artifact_commit_sha256": commit_hash,
            "objective_passed": result["objective_passed"],
            "objective_total": result["objective_total"],
            "execution_valid": result["execution_valid"],
            "skill_invoked": metadata.get("skill_invoked"),
            "assertions": assertions,
            "output": output,
        }
        proof_records.append(record)
        csv_rows.append(
            {
                "case_id": case_id,
                "variant": variant,
                "run_number": run_number,
                "model": result.get("model"),
                "objective_passed": result["objective_passed"],
                "objective_total": result["objective_total"],
                "objective_pass_rate": result["objective_pass_rate"],
                "execution_valid": str(result["execution_valid"]).lower(),
                "skill_invoked": str(bool(metadata.get("skill_invoked"))).lower(),
                "elapsed_ms": metadata.get("elapsed_ms"),
                "total_tokens": metadata.get("total_tokens"),
                "commands": metadata.get("commands"),
                "output_sha256": output_hash,
                "artifact_commit_sha256": commit_hash,
            }
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    outputs_path = args.out_dir / f"{args.name}-outputs.jsonl"
    outputs_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in proof_records),
        encoding="utf-8",
    )
    csv_path = args.out_dir / f"{args.name}-runs.csv"
    fieldnames = list(csv_rows[0])
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(csv_rows)

    by_variant: dict[str, list[dict]] = defaultdict(list)
    by_case_variant: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for result in results:
        by_variant[result["variant"]].append(result)
        by_case_variant[(result["case_id"], result["variant"])].append(result)

    aggregate: dict[str, dict] = {}
    for variant in VARIANTS:
        rows = by_variant[variant]
        cases = sorted({row["case_id"] for row in rows})
        pass_at_1 = []
        all_runs = []
        case_rates = {}
        for case_id in cases:
            case_rows = by_case_variant[(case_id, variant)]
            complete = [row["objective_passed"] == row["objective_total"] for row in case_rows]
            pass_at_1.append(sum(complete) / len(complete))
            all_runs.append(all(complete))
            case_rates[case_id] = mean([row["objective_pass_rate"] for row in case_rows])
        aggregate[variant] = {
            "objective_pass_rate": mean([row["objective_pass_rate"] for row in rows]),
            "mean_pass_at_1": mean(pass_at_1),
            "all_runs_pass_rate": mean([float(value) for value in all_runs]),
            "median_elapsed_ms": statistics.median(row["metadata"]["elapsed_ms"] for row in rows),
            "median_total_tokens": statistics.median(row["metadata"]["total_tokens"] for row in rows),
            "command_count_sum": sum(row["metadata"].get("commands", 0) for row in rows),
            "case_objective_pass_rate": case_rates,
        }

    current_tree = git("rev-parse", f"{args.evaluated_sha}:skills/good-pr")
    baseline_tree = git("rev-parse", f"{args.baseline_sha}:skills/good-pr")
    summary_path = args.out_dir / f"{args.name}.json"
    summary = {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "exploratory_visible_tune_cases",
        "interpretation": "Visible tune cases only; statistics are descriptive, not hidden-holdout confirmation.",
        "protocol": {
            "manifest": str(args.manifest.relative_to(ROOT)),
            "split": "tune",
            "model": args.model,
            "reasoning_effort": "low",
            "runs_per_variant": args.runs_per_variant,
            "cases": len(manifest["cases"]),
            "variants": list(VARIANTS),
            "total_runs": expected,
            "objective_assertions_only": True,
            "qualitative_judges_completed": False,
        },
        "revisions": {
            "harness_version": args.harness_version,
            "harness_git_sha": args.harness_sha,
            "evaluated_good_pr_git_sha": args.evaluated_sha,
            "evaluated_skill_git_tree": current_tree,
            "baseline_git_sha": args.baseline_sha,
            "baseline_skill_git_tree": baseline_tree,
            "baseline_snapshot_content_sha256": hash_tree(args.baseline_snapshot),
            "manifest_sha256": sha256_file(args.manifest),
            "run_matrix": str(csv_path.relative_to(ROOT)),
            "run_matrix_sha256": sha256_file(csv_path),
            "sanitized_outputs": str(outputs_path.relative_to(ROOT)),
            "sanitized_outputs_sha256": sha256_file(outputs_path),
            "canonical_tree_hash_format": "sha256 over sorted '<mode> <relative-path>\\0<bytes>\\0' records",
        },
        "execution_integrity": {
            "complete_artifact_sets": len(proof_records),
            "missing_outputs": 0,
            "execution_errors": sum(not row["execution_valid"] for row in results),
            "model_metadata_matches": sum(row.get("model") == args.model for row in results),
            "no_skill_runs": len(by_variant["without_skill"]),
            "no_skill_invocations": sum(bool(row["metadata"].get("skill_invoked")) for row in by_variant["without_skill"]),
        },
        "final_frozen_run": aggregate,
        "with_skill_vs_without_skill": report.get("paired_summary"),
        "limitations": [
            "All cases are visible tune cases and no qualitative judges were completed.",
            "Harness v0.6.0 metadata does not stamp manifest or skill-tree identity; this bundle binds outputs to a clean committed source revision and verifies the final skill tree is unchanged.",
            "Sanitized outputs omit provider events, traces, stderr, and other metadata; the committed assertion decisions and output text are the review surface.",
            "Model execution is nondeterministic; rerunning verifies the protocol, not byte-for-byte output recreation.",
        ],
        "runner_issue": "https://github.com/adewale/skill-eval-harness/issues/45",
    }
    write_json(summary_path, summary)
    print(f"wrote {summary_path}, {csv_path}, and {outputs_path}")
    return verify_summary(summary_path)


def verify_summary(summary_path: Path) -> int:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    revisions = summary["revisions"]
    manifest = ROOT / summary["protocol"]["manifest"]
    csv_path = ROOT / revisions["run_matrix"]
    outputs_path = ROOT / revisions["sanitized_outputs"]
    checks = {
        "manifest": (manifest, revisions["manifest_sha256"]),
        "run matrix": (csv_path, revisions["run_matrix_sha256"]),
        "sanitized outputs": (outputs_path, revisions["sanitized_outputs_sha256"]),
    }
    for label, (path, expected) in checks.items():
        actual = sha256_file(path)
        if actual != expected:
            raise SystemExit(f"{label} hash mismatch: {actual} != {expected}")

    records = [json.loads(line) for line in outputs_path.read_text(encoding="utf-8").splitlines()]
    record_by_id = {identity(record): record for record in records}
    if len(record_by_id) != len(records):
        raise SystemExit("duplicate identities in sanitized outputs")
    for record in records:
        if sha256_bytes(record["output"].encode()) != record["output_sha256"]:
            raise SystemExit(f"output hash mismatch: {identity(record)}")
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != len(records):
        raise SystemExit("run matrix and sanitized output counts differ")
    for row in rows:
        key = row["case_id"], row["variant"], int(row["run_number"])
        record = record_by_id.get(key)
        if not record or row["output_sha256"] != record["output_sha256"]:
            raise SystemExit(f"run matrix output binding mismatch: {key}")

    current_tree = git("rev-parse", "HEAD:skills/good-pr")
    if current_tree != revisions["evaluated_skill_git_tree"]:
        raise SystemExit("installed skill tree changed after the evaluated source commit")
    baseline = ROOT / "evals/baselines/good-pr-8e613be"
    if hash_tree(baseline) != revisions["baseline_snapshot_content_sha256"]:
        raise SystemExit("frozen baseline snapshot content hash mismatch")
    expected = summary["protocol"]["total_runs"]
    if len(records) != expected or summary["execution_integrity"]["complete_artifact_sets"] != expected:
        raise SystemExit("proof bundle does not contain the declared complete run matrix")
    print(f"OK: verified {expected} eval outputs against manifest, run matrix, and skill trees")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--manifest", type=Path, required=True)
    build_parser.add_argument("--runs", type=Path, required=True)
    build_parser.add_argument("--report", type=Path, required=True)
    build_parser.add_argument("--evaluated-sha", required=True)
    build_parser.add_argument("--baseline-sha", required=True)
    build_parser.add_argument("--baseline-snapshot", type=Path, required=True)
    build_parser.add_argument("--harness-sha", required=True)
    build_parser.add_argument("--harness-version", default="0.6.0")
    build_parser.add_argument("--model", default="gpt-5.4")
    build_parser.add_argument("--runs-per-variant", type=int, default=3)
    build_parser.add_argument("--name", default="visual-evidence-gpt-5.4")
    build_parser.add_argument("--out-dir", type=Path, default=ROOT / "evals/results")
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("summary", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "build":
        return build(args)
    return verify_summary(args.summary)


if __name__ == "__main__":
    raise SystemExit(main())
