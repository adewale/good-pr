from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/analyze_pr_visual_evidence.py"
SPEC = importlib.util.spec_from_file_location("pr_visual_corpus", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class CorpusAnalysisTests(unittest.TestCase):
    def test_counts_pinned_mutable_and_honest_absence(self) -> None:
        sha = "a" * 40
        prs = [
            {
                "repository": {"nameWithOwner": "adewale/charts"},
                "number": 1,
                "title": "Strong renderer evidence",
                "url": "https://github.com/adewale/charts/pull/1",
                "createdAt": "2026-07-16T00:00:00Z",
                "body": f"""## Visual evidence
Before and after. Regenerate with `npm run evidence`.
![Before: overlap](https://raw.githubusercontent.com/adewale/charts/{sha}/before.png)
What to inspect: label clearance. Contact sheet. SHA-256 receipt.
""",
            },
            {
                "repository": {"nameWithOwner": "external/project"},
                "number": 2,
                "title": "Mutable evidence",
                "url": "https://github.com/external/project/pull/2",
                "createdAt": "2026-07-15T00:00:00Z",
                "body": """![After](https://raw.githubusercontent.com/external/project/feature/output.png)
![Relative evidence](docs/output.png)
""",
            },
            {
                "repository": {"nameWithOwner": "adewale/charts"},
                "number": 3,
                "title": "No pixels changed",
                "url": "https://github.com/adewale/charts/pull/3",
                "createdAt": "2026-07-14T00:00:00Z",
                "body": "## Screenshots\nNot applicable: no visual change because output is byte-identical.",
            },
        ]
        report = MODULE.analyze(prs, "adewale", limit=3)
        self.assertEqual(3, report["total_authored_prs"])
        self.assertEqual(2, report["self_owned_repo_prs"])
        self.assertEqual(2, report["prs_with_images"])
        self.assertEqual(1, report["sha_pinned_images"])
        self.assertEqual(2, report["mutable_repo_image_urls"])
        self.assertEqual(1, report["explicit_no_screenshot_rationales"])
        self.assertEqual("gh search prs --author adewale --limit 3", report["method"]["query"])
        self.assertTrue(report["method"]["search_limit_reached"])

    def test_nonrendered_image_examples_are_excluded(self) -> None:
        body = """<!-- ![Commented](commented.png) -->

```markdown
![Fenced](fenced.png)
```

`![Inline](inline.png)`

![Rendered](rendered.png)
"""
        self.assertEqual([("Rendered", "rendered.png")], MODULE.extract_images(body))


if __name__ == "__main__":
    unittest.main()
