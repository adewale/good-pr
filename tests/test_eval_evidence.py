from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_eval_evidence.py"
SPEC = importlib.util.spec_from_file_location("build_eval_evidence", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class EvalEvidenceTests(unittest.TestCase):
    def test_repo_relative_accepts_cli_relative_path(self) -> None:
        self.assertEqual(
            Path("evals/visual-evidence-benchmark.json"),
            MODULE.repo_relative(Path("evals/visual-evidence-benchmark.json")),
        )

    def test_repo_relative_rejects_path_outside_repo(self) -> None:
        with self.assertRaisesRegex(SystemExit, "path must be inside the repository"):
            MODULE.repo_relative(ROOT.parent / "outside.json")

    def test_tree_hash_binds_paths_modes_and_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a.txt"
            first.write_text("alpha\n", encoding="utf-8")
            original = MODULE.hash_tree(root)
            first.write_text("beta\n", encoding="utf-8")
            self.assertNotEqual(original, MODULE.hash_tree(root))
            first.write_text("alpha\n", encoding="utf-8")
            nested = root / "nested"
            nested.mkdir()
            (nested / "a.txt").write_text("alpha\n", encoding="utf-8")
            self.assertNotEqual(original, MODULE.hash_tree(root))

    def test_frozen_baseline_matches_historical_git_tree(self) -> None:
        snapshot = ROOT / "evals/baselines/good-pr-8e613be"
        self.assertEqual(
            MODULE.hash_git_tree(
                "8e613beba912411217ae89b82fadb081a4380bb5", "skills/good-pr"
            ),
            MODULE.hash_tree(snapshot),
        )

    def test_variant_comparison_reports_regressions_and_exact_sign_flip(self) -> None:
        aggregate = {
            "candidate": {
                "objective_pass_rate": 0.75,
                "case_objective_pass_rate": {"a": 1.0, "b": 0.5},
            },
            "reference": {
                "objective_pass_rate": 0.5,
                "case_objective_pass_rate": {"a": 0.5, "b": 0.5},
            },
        }
        comparison = MODULE.compare_variants(aggregate, "candidate", "reference")
        self.assertEqual(0.25, comparison["absolute_delta"])
        self.assertEqual([], comparison["negative_delta_cases"])
        self.assertEqual(1.0, comparison["significance"]["p_value"])

    def test_focused_cases_match_shared_manifest(self) -> None:
        import json

        focused = json.loads((ROOT / "evals/visual-evidence-benchmark.json").read_text())
        shared = json.loads((ROOT / "evals/shared-benchmark.json").read_text())
        shared_by_id = {case["id"]: case for case in shared["cases"]}
        self.assertEqual(9, len(focused["cases"]))
        for case in focused["cases"]:
            self.assertEqual(case, shared_by_id[case["id"]])


if __name__ == "__main__":
    unittest.main()
