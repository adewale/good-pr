from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "evals/shared-benchmark.json").read_text(encoding="utf-8"))
VISUAL_MANIFEST = json.loads(
    (ROOT / "evals/visual-evidence-benchmark.json").read_text(encoding="utf-8")
)


def assertion(case_id: str, assertion_name: str) -> dict:
    case = next(item for item in MANIFEST["cases"] if item["id"] == case_id)
    return next(item for item in case["assertions"] if item["name"] == assertion_name)


def passes(assertion_spec: dict, output: str) -> bool:
    if assertion_spec["type"] == "contains_any":
        return any(value.casefold() in output.casefold() for value in assertion_spec["values"])
    if assertion_spec["type"] == "regex":
        return re.search(assertion_spec["pattern"], output) is not None
    raise AssertionError(f"unsupported assertion type: {assertion_spec['type']}")


class EvalAssertionTests(unittest.TestCase):
    def test_skill_paths_resolve_from_the_manifest_directory(self) -> None:
        manifest_dir = ROOT / "evals"
        for manifest in (MANIFEST, VISUAL_MANIFEST):
            for key in ("skill_paths", "old_skill_paths"):
                for relative_path in manifest.get(key, []):
                    self.assertTrue((manifest_dir / relative_path).resolve().is_file(), relative_path)
        for ablation in MANIFEST["ablations"]:
            relative_path = ablation["target"]["skill_root"]
            self.assertTrue((manifest_dir / relative_path).resolve().is_file(), relative_path)

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


if __name__ == "__main__":
    unittest.main()
