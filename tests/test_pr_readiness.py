from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/good-pr/scripts/check-pr-readiness.sh"


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True)


class ReadinessIntegrationTests(unittest.TestCase):
    def make_repo(self, directory: Path) -> None:
        self.assertEqual(0, run(["git", "init", "-b", "main"], directory).returncode)
        self.assertEqual(0, run(["git", "config", "user.name", "Test User"], directory).returncode)
        self.assertEqual(0, run(["git", "config", "user.email", "test@example.com"], directory).returncode)
        (directory / "README.md").write_text("baseline\n", encoding="utf-8")
        self.assertEqual(0, run(["git", "add", "README.md"], directory).returncode)
        self.assertEqual(
            0,
            run(["git", "-c", "commit.gpgsign=false", "commit", "-m", "baseline"], directory).returncode,
        )
        self.assertEqual(0, run(["git", "checkout", "-b", "feature"], directory).returncode)
        (directory / "button.tsx").write_text("export const Button = () => null;\n", encoding="utf-8")
        self.assertEqual(0, run(["git", "add", "button.tsx"], directory).returncode)
        self.assertEqual(
            0,
            run(["git", "-c", "commit.gpgsign=false", "commit", "-m", "change button"], directory).returncode,
        )

    def test_wrapper_propagates_missing_body_and_audit_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.make_repo(repo)

            missing = run(["bash", str(SCRIPT), "main", str(repo / "missing.md")], repo)
            self.assertEqual(1, missing.returncode, missing.stdout)
            self.assertIn("PR body file does not exist", missing.stdout)

            body = repo / "body.md"
            body.write_text("## What\n\nFix renderer clipping in generated charts.\n", encoding="utf-8")
            failed = run(["bash", str(SCRIPT), "main", str(body)], repo)
            self.assertEqual(1, failed.returncode, failed.stdout)
            self.assertIn("Visual Evidence Audit (generated)", failed.stdout)
            self.assertIn("Visual-evidence audit found blocking issues", failed.stdout)

    def test_wrapper_uses_ui_fallback_and_accepts_honest_no_impact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.make_repo(repo)
            body = repo / "body.md"

            body.write_text("## What\n\nChange the button implementation.\n", encoding="utf-8")
            missing_evidence = run(["bash", str(SCRIPT), "main", str(body)], repo)
            self.assertEqual(1, missing_evidence.returncode, missing_evidence.stdout)
            self.assertIn("Visual Evidence Audit (ui)", missing_evidence.stdout)

            body.write_text(
                "## Screenshots\n\nNot applicable because there is no visual change; rendered pixels are identical.\n",
                encoding="utf-8",
            )
            accepted = run(["bash", str(SCRIPT), "main", str(body)], repo)
            self.assertEqual(0, accepted.returncode, accepted.stdout)
            self.assertIn("no-visual-impact", accepted.stdout)


if __name__ == "__main__":
    unittest.main()
