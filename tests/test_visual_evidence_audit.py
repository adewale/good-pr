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
SPEC = importlib.util.spec_from_file_location("visual_evidence_lint", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

BASE_SHA = "1" * 40
HEAD_SHA = "2" * 40


def generated_body(before_ref: str = BASE_SHA, after_ref: str = HEAD_SHA) -> str:
    return f"""## Visual evidence

Baseline SHA: `{BASE_SHA}`
Current SHA: `{HEAD_SHA}`

![Before: clipped label](https://raw.githubusercontent.com/acme/charts/{before_ref}/before.png)
![After: clear label](https://raw.githubusercontent.com/acme/charts/{after_ref}/after.png)
"""


class LintTests(unittest.TestCase):
    @staticmethod
    def codes(result: dict, level: str | None = None) -> set[str]:
        return {
            finding["code"]
            for finding in result["findings"]
            if level is None or finding["level"] == level
        }

    def test_generated_evidence_passes_mechanical_checks(self) -> None:
        result = MODULE.audit(
            generated_body(),
            "generated",
            expected_base_sha=BASE_SHA,
            expected_current_sha=HEAD_SHA,
        )
        self.assertEqual("pass", result["status"])
        self.assertEqual(2, result["media_count"])
        self.assertIn("immutable-urls", self.codes(result, "pass"))

    def test_generated_branch_urls_are_blocking(self) -> None:
        result = MODULE.audit(generated_body("feature", "feature"), "generated")
        self.assertIn("immutable-urls", self.codes(result, "error"))

    def test_generated_labels_must_match_supplied_revisions_and_differ(self) -> None:
        mismatched = MODULE.audit(
            generated_body(),
            "generated",
            expected_base_sha="3" * 40,
            expected_current_sha="4" * 40,
        )
        self.assertIn("baseline-provenance", self.codes(mismatched, "error"))
        self.assertIn("current-provenance", self.codes(mismatched, "error"))

        same = MODULE.audit(generated_body().replace(BASE_SHA, HEAD_SHA), "generated")
        self.assertIn("distinct-revisions", self.codes(same, "error"))

    def test_direct_generated_mode_describes_shape_only_validation(self) -> None:
        result = MODULE.audit(generated_body(), "generated")
        messages = "\n".join(item["message"] for item in result["findings"])
        self.assertIn("shape only", messages)

    def test_ui_accepts_uploaded_screenshots_and_bare_recordings(self) -> None:
        body = """## Screenshots / Recordings

![Before: gray checkout button](https://github.com/user-attachments/assets/11111111-1111-1111-1111-111111111111)
https://github.com/user-attachments/assets/22222222-2222-2222-2222-222222222222
"""
        result = MODULE.audit(body, "ui")
        self.assertEqual(2, result["media_count"])
        self.assertEqual(0, result["errors"])

    def test_kind_none_skips_visual_requirements(self) -> None:
        result = MODULE.audit("## What\n\nNo rendered output changes.\n", "none")
        self.assertEqual("pass", result["status"])
        self.assertFalse(result["findings"])

    def test_auto_detects_media_outside_visual_section(self) -> None:
        body = """## What changed

![After](https://github.com/user-attachments/assets/11111111-1111-1111-1111-111111111111)
"""
        result = MODULE.audit(body, "auto")
        self.assertEqual("ui", result["kind"])
        self.assertEqual("fail", result["status"])
        self.assertIn("visual-section", self.codes(result, "error"))
        self.assertIn("visual-assets", self.codes(result, "error"))

    def test_comments_code_and_inline_examples_do_not_count(self) -> None:
        hidden = f"![Hidden](https://raw.githubusercontent.com/acme/charts/{HEAD_SHA}/hidden.png)"
        bodies = (
            f"## Visual evidence\n\n<!-- {hidden} -->\n",
            f"## Visual evidence\n\n```markdown\n{hidden}\n``` trailing text\n{hidden}\n```\n",
            f"## Visual evidence\n\n    {hidden}\n",
            f"## Visual evidence\n\n`{hidden}`\n",
        )
        for body in bodies:
            with self.subTest(body=body):
                result = MODULE.audit(body, "ui")
                self.assertEqual(0, result["media_count"])
                self.assertIn("visual-assets", self.codes(result, "error"))

    def test_comment_marker_in_inline_code_does_not_hide_later_media(self) -> None:
        body = f"""## Visual evidence

`<!--` is an example, not a comment opener.
![Visible: chart](https://raw.githubusercontent.com/acme/charts/{HEAD_SHA}/chart.png)
"""
        self.assertEqual(1, MODULE.audit(body, "ui")["media_count"])

    def test_reference_definitions_outside_section_are_resolved(self) -> None:
        body = f"""## Visual evidence

![Before: clipped label][before]
![After: clear label][]

## Tests

[before]: https://raw.githubusercontent.com/acme/charts/{BASE_SHA}/before.png
[After: clear label]: https://raw.githubusercontent.com/acme/charts/{HEAD_SHA}/after.png
"""
        result = MODULE.audit(body, "ui")
        self.assertEqual(2, result["media_count"])

    def test_malformed_doubled_backticks_are_blocking(self) -> None:
        body = """## Screenshots

![Before: checkout](``https://example.com/before.png``)
"""
        self.assertIn("markdown-image-url", self.codes(MODULE.audit(body, "ui"), "error"))

    def test_generated_external_and_uploaded_assets_warn(self) -> None:
        body = f"""## Visual evidence

Baseline SHA: `{BASE_SHA}`
Current SHA: `{HEAD_SHA}`
![External chart](https://example.com/chart.png)
![Uploaded chart](https://github.com/user-attachments/assets/11111111-1111-1111-1111-111111111111)
"""
        result = MODULE.audit(body, "generated")
        self.assertIn("external-url-provenance", self.codes(result, "warning"))
        self.assertIn("generated-upload-provenance", self.codes(result, "warning"))

    def test_unsupported_url_schemes_are_blocking(self) -> None:
        body = f"""## Visual evidence

Baseline SHA: `{BASE_SHA}`
Current SHA: `{HEAD_SHA}`
![Local file](file:///tmp/chart.png)
![Inline data](data:image/png;base64,AAAA)
"""
        result = MODULE.audit(body, "generated")
        self.assertEqual("fail", result["status"])
        self.assertIn("unsupported-url-scheme", self.codes(result, "error"))

    def test_cli_json_and_strict_warning_exit(self) -> None:
        body = """## Screenshots

![](https://github.com/user-attachments/assets/11111111-1111-1111-1111-111111111111)
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "body.md"
            path.write_text(body, encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--kind", "ui", "--strict", "--format", "json", str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(1, completed.returncode)
        self.assertEqual("warn", json.loads(completed.stdout)["status"])


if __name__ == "__main__":
    unittest.main()
