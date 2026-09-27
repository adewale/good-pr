from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The harness release the manifests are validated against (evals/shared-harness.md).
HARNESS_PIN = "skill-eval-harness==0.6.0"
MANIFEST = json.loads((ROOT / "evals/shared-benchmark.json").read_text(encoding="utf-8"))
VISUAL_MANIFEST = json.loads(
    (ROOT / "evals/visual-evidence-benchmark.json").read_text(encoding="utf-8")
)


def assertion(case_id: str, assertion_name: str) -> dict:
    case = next(item for item in MANIFEST["cases"] if item["id"] == case_id)
    return next(item for item in case["assertions"] if item["name"] == assertion_name)


def harness_command() -> list[str]:
    """The pinned harness CLI: $SKILL_BENCHMARK if set, else `skill-benchmark` on
    PATH (CI installs the pin), else the pin through uvx. Never a silent skip: with
    no harness available the path test fails and says how to install it."""
    override = os.environ.get("SKILL_BENCHMARK")
    if override:
        return shlex.split(override)
    if shutil.which("skill-benchmark"):
        return ["skill-benchmark"]
    if shutil.which("uvx"):
        return ["uvx", "--from", HARNESS_PIN, "skill-benchmark"]
    raise AssertionError(
        f"the skill-path test runs the real harness; install it with "
        f"`pip install {HARNESS_PIN}` (or `uv tool install {HARNESS_PIN}`), "
        "or set SKILL_BENCHMARK to its command"
    )


def passes(assertion_spec: dict, output: str) -> bool:
    if assertion_spec["type"] == "contains_any":
        return any(value.casefold() in output.casefold() for value in assertion_spec["values"])
    if assertion_spec["type"] == "regex":
        return re.search(assertion_spec["pattern"], output) is not None
    raise AssertionError(f"unsupported assertion type: {assertion_spec['type']}")


class HarnessPrepareTests(unittest.TestCase):
    """Ask the real pinned harness where each arm's skill lives, instead of
    re-deriving its path rules here. The harness resolves skill paths in
    evals/shared-benchmark.json from the repository root but those in any other
    manifest file from that file's directory, so the same `../skills/...` string
    is right in one manifest and a nonexistent with-skill mount in the other."""

    def prepared_rows(self, manifest: str, workdir: Path, *extra: str) -> list[dict]:
        out = workdir / "tasks.jsonl"
        command = [*harness_command(), "prepare", manifest, "--allow-missing-prompts",
                   "--out", str(out), *extra]
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, f"{shlex.join(command)} failed:\n{proc.stderr}")
        rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertTrue(rows, "prepare emitted no tasks")
        return rows

    def assert_arm(self, rows: list[dict], variant: str, expected: list[Path]) -> None:
        arm = [row for row in rows if row["variant"] == variant]
        self.assertTrue(arm, f"prepare emitted no {variant} tasks")
        for row in arm:
            self.assertEqual([Path(p) for p in row["skill_paths"]], [p.resolve() for p in expected],
                             f"{row['case_id']}/{variant}")
            for path in row["skill_paths"]:
                self.assertTrue(Path(path).is_file(), f"{row['case_id']}/{variant} mounts missing {path}")

    def test_shared_benchmark_mounts_the_real_skill_and_every_ablation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workdir = Path(td)
            rows = self.prepared_rows(
                "evals/shared-benchmark.json", workdir,
                "--include-ablations", "--ablation-dir", str(workdir / "ablations"))
            self.assert_arm(rows, "with_skill", [ROOT / "skills/good-pr/SKILL.md"])
            self.assertTrue(all(not row["skill_paths"] for row in rows if row["variant"] == "without_skill"))
            for ablation in MANIFEST["ablations"]:
                variant = f"ablation:{ablation['id']}"
                arm = [row for row in rows if row["variant"] == variant]
                self.assertTrue(arm, f"prepare emitted no {variant} tasks")
                for row in arm:
                    self.assertTrue(row["skill_paths"], f"{row['case_id']}/{variant}")
                    for path in row["skill_paths"]:
                        self.assertTrue(Path(path).is_file(), f"{row['case_id']}/{variant} mounts missing {path}")
                        self.assertIn(workdir / "ablations", Path(path).parents)

    def test_visual_benchmark_mounts_the_real_skill_and_the_frozen_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            rows = self.prepared_rows(
                "evals/visual-evidence-benchmark.json", Path(td), "--include-old-skill")
            self.assert_arm(rows, "with_skill", [ROOT / "skills/good-pr/SKILL.md"])
            self.assert_arm(rows, "old_skill", [ROOT / "evals/baselines/good-pr-8e613be/SKILL.md"])


class EvalAssertionTests(unittest.TestCase):
    def test_honest_baseline_negative_guard_understands_negation(self) -> None:
        pattern = assertion(
            "neg-new-surface-no-fake-before",
            "does-not-demand-fake-before",
        )["pattern"]
        self.assertIsNone(re.search(pattern, "There is no need to invent a before image."))
        self.assertIsNotNone(re.search(pattern, "You should invent a before image."))

    def test_no_visible_impact_guard_understands_negation(self) -> None:
        pattern = assertion(
            "neg-ui-file-no-visible-impact",
            "does-not-demand-ui-file-screenshots",
        )["pattern"]
        self.assertIsNone(re.search(pattern, "There is no need to attach screenshots."))
        self.assertIsNotNone(re.search(pattern, "You should attach before/after screenshots."))

    def test_alt_assertion_accepts_markdown_code_formatting(self) -> None:
        values = assertion(
            "pos-generated-evidence-durability-audit",
            "requires-descriptive-alt-text",
        )["values"]
        output = "Add meaningful `alt` text to every HTML image."
        self.assertTrue(any(value.casefold() in output.casefold() for value in values))

    def test_visible_tune_assertions_accept_semantically_equivalent_phrasing(self) -> None:
        examples = [
            ("pos-renderer-evidence-provenance", "suggests-captions", "Label the pair with the defect."),
            ("pos-renderer-evidence-provenance", "suggests-captions", "Tell reviewers what to inspect."),
            ("neg-new-surface-no-fake-before", "accepts-honest-unsupported-baseline", "You should not invent a fake before image."),
            ("neg-ui-file-no-visible-impact", "accepts-no-visible-impact-rationale", "You do not need before/after screenshots."),
            ("neg-ui-file-no-visible-impact", "accepts-no-visible-impact-rationale", "Screenshots are not proportionate evidence."),
            ("pos-generated-evidence-durability-audit", "requires-immutable-image-refs", "Use full commit-SHA URLs."),
            ("pos-malformed-visual-markdown", "detects-missing-alt", "The HTML images need `alt` text."),
            ("pos-visual-claim-needs-independent-oracle", "requires-discriminating-visual-test", "Add a test that measures the distance and fails on regression."),
            ("pos-generated-proof-contract-end-to-end", "requires-identical-input", "Use the same fixture at both revisions."),
            ("pos-generated-proof-contract-end-to-end", "requires-material-limitation", "State what the image cannot prove."),
            ("neg-subjective-generated-proof-no-overbuild", "recognizes-subjective-boundary", "This is a subjective judgment; do not invent a metric."),
        ]
        for case_id, assertion_name, output in examples:
            with self.subTest(case_id=case_id, assertion=assertion_name):
                self.assertTrue(passes(assertion(case_id, assertion_name), output))

    def test_policy_exception_does_not_trigger_the_ui_demand_guard(self) -> None:
        pattern = assertion(
            "neg-ui-file-no-visible-impact",
            "does-not-demand-ui-file-screenshots",
        )["pattern"]
        policy_exception = 'Follow a repository rule like "every UI PR must attach screenshots".'
        self.assertIsNone(re.search(pattern, policy_exception))
        self.assertIsNotNone(re.search(pattern, "You should attach screenshots."))

    def test_proof_infrastructure_guard_understands_negation(self) -> None:
        pattern = next(
            item
            for case in VISUAL_MANIFEST["cases"]
            if case["id"] == "neg-subjective-generated-proof-no-overbuild"
            for item in case["assertions"]
            if item["name"] == "does-not-demand-proof-only-infrastructure"
        )["pattern"]
        self.assertIsNone(re.search(pattern, "You should not build new infrastructure for this proof."))
        self.assertIsNone(re.search(pattern, "You should avoid adding a pixel-diff service."))
        self.assertIsNotNone(re.search(pattern, "You should build a pixel-diff service for this proof."))


if __name__ == "__main__":
    unittest.main()
