from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/good-pr/scripts/check-visual-evidence.py"
SPEC = importlib.util.spec_from_file_location("visual_evidence_audit", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

BASE_SHA = "1" * 40
HEAD_SHA = "2" * 40


def generated_body(before_ref: str = BASE_SHA, after_ref: str = HEAD_SHA) -> str:
    return f"""## Visual evidence

Claim: the label clears the container border without moving the arrow.

Input/fixture: `fixtures/label-overlap.json` with the same renderer config at both revisions.

Baseline SHA: `{BASE_SHA}`

Current SHA: `{HEAD_SHA}`

| Before | After | Why | What to inspect |
|---|---|---|---|
| ![Before: label overlaps the container border](https://raw.githubusercontent.com/acme/charts/{before_ref}/docs/before.png) | ![After: label clears the container border](https://raw.githubusercontent.com/acme/charts/{after_ref}/docs/after.png) | The old anchor used the label centre. | The label clears the border; the arrow is unchanged as a control. |

Regenerate with `python3 scripts/render-evidence.py`.

Independent check: `tests/test_label_geometry.py` asserts label-to-border clearance.

Limitation: the images cover this fixture and font stack; they do not prove every label layout.
"""


class AuditTests(unittest.TestCase):
    def codes(self, result: dict, level: str | None = None) -> set[str]:
        return {
            finding["code"]
            for finding in result["findings"]
            if level is None or finding["level"] == level
        }

    def test_complete_generated_evidence_passes(self) -> None:
        result = MODULE.audit(generated_body(), "generated")
        self.assertEqual("pass", result["status"])
        self.assertEqual(0, result["errors"])
        self.assertIn("immutable-urls", self.codes(result, "pass"))
        self.assertIn("regeneration-command", self.codes(result, "pass"))
        self.assertIn("review-cue", self.codes(result, "pass"))

    def test_generated_branch_urls_are_blocking(self) -> None:
        result = MODULE.audit(generated_body("feature-branch", "feature-branch"), "generated")
        self.assertEqual("fail", result["status"])
        self.assertIn("immutable-urls", self.codes(result, "error"))

    def test_generated_evidence_requires_regeneration_command(self) -> None:
        body = generated_body().replace(
            "Regenerate with `python3 scripts/render-evidence.py`.",
            "The images were checked manually.",
        )
        result = MODULE.audit(body, "generated")
        self.assertIn("regeneration-command", self.codes(result, "error"))

    def test_generated_evidence_requires_labelled_claim_input_and_head(self) -> None:
        replacements = {
            "Claim: the label clears the container border without moving the arrow.\n\n": "",
            "Input/fixture: `fixtures/label-overlap.json` with the same renderer config at both revisions.\n\n": "",
            f"Current SHA: `{HEAD_SHA}`\n\n": "",
        }
        body = generated_body()
        for source, replacement in replacements.items():
            body = body.replace(source, replacement)
        result = MODULE.audit(body, "generated")
        self.assertIn("visible-claim", self.codes(result, "error"))
        self.assertIn("same-input", self.codes(result, "error"))
        self.assertIn("current-provenance", self.codes(result, "error"))

    def test_generated_evidence_warns_without_explicit_limitation(self) -> None:
        body = generated_body().replace(
            "Limitation: the images cover this fixture and font stack; they do not prove every label layout.\n",
            "",
        )
        result = MODULE.audit(body, "generated")
        self.assertIn("evidence-limitation", self.codes(result, "warning"))

    def test_receipt_can_replace_regeneration_command(self) -> None:
        body = generated_body().replace(
            "Regenerate with `python3 scripts/render-evidence.py`.",
            "Receipt: `evidence/receipt.json` records input SHA-256 and both output SHA-256 values.",
        )
        result = MODULE.audit(body, "generated")
        self.assertNotIn("regeneration-command", self.codes(result, "error"))
        self.assertIn("evidence-receipt", self.codes(result, "pass"))

    def test_new_surface_can_preserve_an_honest_nonvisual_baseline(self) -> None:
        body = f"""## Visual evidence

Claim: the previously unsupported radar chart now renders six bounded axes.
Input/fixture: `fixtures/radar.json`.

Before: no prior renderable baseline; the old version reports unsupported syntax
at immutable commit `{BASE_SHA}`. No fabricated image is used.

After:
![After: radar chart renders all six axes](https://raw.githubusercontent.com/acme/charts/{HEAD_SHA}/docs/radar-after.png)

Current SHA: `{HEAD_SHA}`.
Regenerate with `npm run render-radar-evidence`.
What to inspect: six axes, complete labels, and bounded legend.
Independent check: `tests/radar-geometry.test.ts` asserts all six axes and bounded legend geometry.
Limitation: this proves the checked fixture, not every radar dataset.
"""
        result = MODULE.audit(body, "generated")
        self.assertEqual("pass", result["status"])
        self.assertIn("causal-comparison", self.codes(result, "pass"))
        self.assertIn("baseline-provenance", self.codes(result, "pass"))

    def test_ordinary_ui_accepts_uploaded_hand_taken_screenshots(self) -> None:
        body = """## Screenshots / Recordings

Before: ![Before: gray checkout button](https://github.com/user-attachments/assets/11111111-1111-1111-1111-111111111111)

After: ![After: blue checkout button](https://github.com/user-attachments/assets/22222222-2222-2222-2222-222222222222)
"""
        result = MODULE.audit(body, "ui")
        self.assertEqual("pass", result["status"])
        self.assertNotIn("regeneration-command", self.codes(result, "error"))

    def test_explicit_no_visual_impact_is_accepted(self) -> None:
        body = """## Screenshots

Not applicable because there is no visual change; this only changes keyboard
event handling and the rendered pixels remain byte-identical.
"""
        result = MODULE.audit(body, "ui")
        self.assertEqual("pass", result["status"])
        self.assertIn("no-visual-impact", self.codes(result, "pass"))

    def test_auto_detects_generated_change_without_existing_evidence(self) -> None:
        body = "## What\n\nFix renderer clipping in generated charts."
        result = MODULE.audit(body, "auto")
        self.assertEqual("generated", result["kind"])
        self.assertIn("visual-section", self.codes(result, "error"))
        self.assertIn("visual-assets", self.codes(result, "error"))

    def test_generated_output_is_not_exempted_by_no_ui_change(self) -> None:
        body = """## Visual evidence

The generated chart output changes, but this does not change the UI.
"""
        result = MODULE.audit(body, "generated")
        self.assertIn("visual-assets", self.codes(result, "error"))
        self.assertNotIn("no-visual-impact", self.codes(result, "pass"))

    def test_commented_evidence_is_not_counted(self) -> None:
        body = f"""## Visual evidence

<!--
Baseline commit `{BASE_SHA}`.
![Before: clipped label](https://raw.githubusercontent.com/acme/charts/{BASE_SHA}/before.png)
![After: clear label](https://raw.githubusercontent.com/acme/charts/{HEAD_SHA}/after.png)
Regenerate with `python3 scripts/render.py`.
What to inspect: label clearance. Regression test asserts clearance.
-->
"""
        result = MODULE.audit(body, "generated")
        self.assertEqual(0, result["media_count"])
        self.assertIn("visual-assets", self.codes(result, "error"))

    def test_unclosed_comment_and_indented_code_are_not_counted(self) -> None:
        hidden = generated_body()
        for body in (f"## Visual evidence\n\n<!--\n{hidden}", "    " + hidden.replace("\n", "\n    ")):
            with self.subTest(body=body[:30]):
                result = MODULE.audit(body, "generated")
                self.assertEqual(0, result["media_count"])
                self.assertIn("visual-assets", self.codes(result, "error"))

    def test_reference_style_images_are_supported(self) -> None:
        body = generated_body().replace(
            f"![Before: label overlaps the container border](https://raw.githubusercontent.com/acme/charts/{BASE_SHA}/docs/before.png)",
            "![Before: label overlaps the container border][before-image]",
        ).replace(
            f"![After: label clears the container border](https://raw.githubusercontent.com/acme/charts/{HEAD_SHA}/docs/after.png)",
            "![After: label clears the container border][after-image]",
        )
        body += (
            f"\n[before-image]: https://raw.githubusercontent.com/acme/charts/{BASE_SHA}/docs/before.png\n"
            f"[after-image]: https://raw.githubusercontent.com/acme/charts/{HEAD_SHA}/docs/after.png\n"
        )
        result = MODULE.audit(body, "generated")
        self.assertEqual(2, result["media_count"])
        self.assertNotIn("visual-assets", self.codes(result, "error"))

    def test_one_image_cannot_claim_before_and_after(self) -> None:
        body = f"""## Visual evidence

This is the before and after comparison.
![After: label clears the border](https://raw.githubusercontent.com/acme/charts/{HEAD_SHA}/after.png)
"""
        result = MODULE.audit(body, "ui")
        self.assertIn("causal-comparison", self.codes(result, "error"))

    def test_baseline_sha_must_be_explicitly_labelled(self) -> None:
        body = generated_body().replace(
            f"Baseline SHA: `{BASE_SHA}`",
            "Baseline evidence is below.",
        ).replace(
            f"/{BASE_SHA}/docs/before.png",
            f"/{HEAD_SHA}/docs/before.png",
        )
        result = MODULE.audit(body, "generated")
        self.assertIn("baseline-provenance", self.codes(result, "error"))

    def test_baseline_and_current_sha_must_differ(self) -> None:
        body = generated_body().replace(BASE_SHA, HEAD_SHA)
        result = MODULE.audit(body, "generated")
        self.assertIn("baseline-provenance", self.codes(result, "error"))

    def test_expected_git_revisions_must_match_labels(self) -> None:
        result = MODULE.audit(
            generated_body(),
            "generated",
            expected_base_sha="3" * 40,
            expected_current_sha="4" * 40,
        )
        self.assertIn("baseline-provenance", self.codes(result, "error"))
        self.assertIn("current-provenance", self.codes(result, "error"))

    def test_base_sha_label_and_abbreviated_same_revision_are_understood(self) -> None:
        body = generated_body().replace(
            f"Baseline commit `{BASE_SHA}`; current commit `{HEAD_SHA}`.",
            f"Base SHA: `{BASE_SHA[:8]}`; Head SHA: `{HEAD_SHA}`.",
        )
        accepted = MODULE.audit(body, "generated")
        self.assertIn("baseline-provenance", self.codes(accepted, "pass"))

        same = body.replace(BASE_SHA[:8], HEAD_SHA[:8])
        rejected = MODULE.audit(same, "generated")
        self.assertIn("baseline-provenance", self.codes(rejected, "error"))

    def test_bare_github_recording_attachment_is_recognized(self) -> None:
        body = """## Screenshots / Recordings

Before and after recording:
https://github.com/user-attachments/assets/11111111-1111-1111-1111-111111111111
"""
        result = MODULE.audit(body, "ui")
        self.assertEqual(1, result["media_count"])
        self.assertNotIn("visual-assets", self.codes(result, "error"))
        self.assertIn("causal-comparison", self.codes(result, "pass"))

    def test_generated_evidence_warns_without_independent_oracle(self) -> None:
        body = generated_body().replace(
            "Independent check: `tests/test_label_geometry.py` asserts label-to-border clearance.",
            "Reviewed the screenshots manually.",
        )
        result = MODULE.audit(body, "generated")
        self.assertIn("independent-oracle", self.codes(result, "warning"))

    def test_subjective_limitation_can_explain_absent_oracle(self) -> None:
        body = generated_body().replace(
            "Independent check: `tests/test_label_geometry.py` asserts label-to-border clearance.\n\n",
            "",
        ).replace(
            "Limitation: the images cover this fixture and font stack; they do not prove every label layout.",
            "Limitation: visual hierarchy is subjective and no objective metric would establish readability.",
        )
        result = MODULE.audit(body, "generated")
        self.assertIn("independent-oracle", self.codes(result, "pass"))

    def test_unrelated_commands_and_tests_do_not_satisfy_proof_fields(self) -> None:
        body = generated_body().replace(
            "Regenerate with `python3 scripts/render-evidence.py`.",
            "The documentation is reproducible. Run `npm test`.",
        ).replace(
            "Independent check: `tests/test_label_geometry.py` asserts label-to-border clearance.",
            "Unit test covers CLI parsing only.",
        )
        result = MODULE.audit(body, "generated")
        self.assertIn("regeneration-command", self.codes(result, "error"))
        self.assertIn("independent-oracle", self.codes(result, "warning"))

    def test_external_generated_urls_are_not_reported_as_pinned(self) -> None:
        body = generated_body(BASE_SHA, HEAD_SHA).replace(
            f"https://raw.githubusercontent.com/acme/charts/{BASE_SHA}/docs/before.png",
            "https://example.com/before.png",
        ).replace(
            f"https://raw.githubusercontent.com/acme/charts/{HEAD_SHA}/docs/after.png",
            "https://example.com/after.png",
        )
        result = MODULE.audit(body, "generated")
        self.assertNotIn("immutable-urls", self.codes(result, "pass"))
        self.assertIn("external-url-provenance", self.codes(result, "warning"))

    def test_qualified_no_impact_statement_does_not_exempt_visible_change(self) -> None:
        body = """## Screenshots

There is no visual change to layout, but the button color changes from gray to blue.
"""
        result = MODULE.audit(body, "ui")
        self.assertIn("contradictory-no-impact", self.codes(result, "error"))
        self.assertIn("visual-assets", self.codes(result, "error"))

    def test_auto_does_not_treat_react_renderer_callback_as_generated_output(self) -> None:
        body = "## What\n\nRefactor the React renderer callback without changing pixels."
        result = MODULE.audit(body, "auto")
        self.assertEqual("none", result["kind"])

    def test_malformed_doubled_backticks_are_detected(self) -> None:
        body = generated_body().replace(
            f"(https://raw.githubusercontent.com/acme/charts/{BASE_SHA}/docs/before.png)",
            f"(``https://raw.githubusercontent.com/acme/charts/{BASE_SHA}/docs/before.png``)",
        )
        result = MODULE.audit(body, "generated")
        self.assertIn("markdown-image-url", self.codes(result, "error"))

    def test_large_matrix_recommends_contact_sheet(self) -> None:
        images = "\n".join(
            f"![Variant {index}: labels remain clear](https://raw.githubusercontent.com/acme/charts/{HEAD_SHA}/docs/{index}.png)"
            for index in range(13)
        )
        body = generated_body().replace("\nIndependent check:", f"\n{images}\n\nIndependent check:")
        result = MODULE.audit(body, "generated")
        self.assertIn("evidence-volume", self.codes(result, "warning"))

    def test_cli_json_and_strict_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            body_file = Path(tmp) / "body.md"
            body_file.write_text(generated_body(), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--kind", "generated", "--format", "json", str(body_file)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual("pass", json.loads(completed.stdout)["status"])

            warning_body = generated_body().replace(
                "Independent check: `tests/test_label_geometry.py` asserts label-to-border clearance.",
                "Reviewed the screenshots manually.",
            )
            body_file.write_text(warning_body, encoding="utf-8")
            non_strict = subprocess.run(
                [sys.executable, str(SCRIPT), "--kind", "generated", str(body_file)],
                check=False,
                capture_output=True,
                text=True,
            )
            strict = subprocess.run(
                [sys.executable, str(SCRIPT), "--kind", "generated", "--strict", str(body_file)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, non_strict.returncode, non_strict.stdout)
            self.assertEqual(1, strict.returncode, strict.stdout)


if __name__ == "__main__":
    unittest.main()
