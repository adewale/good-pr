from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/good-pr/scripts/check-pr-readiness.py"


def readiness(*args: str) -> list[str]:
    return [sys.executable, str(SCRIPT), *args]


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True)


class ReadinessIntegrationTests(unittest.TestCase):
    def make_repo(self, directory: Path, changed_file: str = "button.tsx") -> None:
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
        (directory / changed_file).write_text("export const Button = () => null;\n", encoding="utf-8")
        self.assertEqual(0, run(["git", "add", changed_file], directory).returncode)
        self.assertEqual(
            0,
            run(["git", "-c", "commit.gpgsign=false", "commit", "-m", "change button"], directory).returncode,
        )

    def test_wrapper_propagates_missing_body_and_lint_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.make_repo(repo)

            missing = run(readiness("main", str(repo / "missing.md")), repo)
            self.assertEqual(1, missing.returncode, missing.stdout)
            self.assertIn("PR body file does not exist", missing.stdout)

            body = repo / "body.md"
            body.write_text("## What\n\nFix renderer clipping in generated charts.\n", encoding="utf-8")
            failed = run(readiness("main", str(body)), repo)
            self.assertEqual(1, failed.returncode, failed.stdout)
            self.assertIn("Visual Evidence Lint (ui)", failed.stdout)
            self.assertIn("Visual-evidence lint found blocking issues", failed.stdout)

    def test_wrapper_uses_ui_fallback_and_allows_explicit_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.make_repo(repo)
            body = repo / "body.md"

            body.write_text("## What\n\nChange the button implementation.\n", encoding="utf-8")
            missing_evidence = run(readiness("main", str(body)), repo)
            self.assertEqual(1, missing_evidence.returncode, missing_evidence.stdout)
            self.assertIn("Visual Evidence Lint (ui)", missing_evidence.stdout)

            body.write_text(
                "## Screenshots\n\nNot applicable because there is no visual change; rendered pixels are identical.\n",
                encoding="utf-8",
            )
            accepted = run(readiness("main", str(body), "none"), repo)
            self.assertEqual(0, accepted.returncode, accepted.stdout)
            self.assertIn("No mechanical visual-evidence checks apply", accepted.stdout)

    def test_wrapper_allows_explicit_generated_kind_for_non_ui_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.make_repo(repo, "renderer.ts")
            body = repo / "body.md"
            body.write_text("## What\n\nFix clipping in Mermaid SVG labels.\n", encoding="utf-8")

            explicit = run(readiness("main", str(body), "generated"), repo)
            self.assertEqual(1, explicit.returncode, explicit.stdout)
            self.assertIn("Visual Evidence Lint (generated)", explicit.stdout)

            invalid = run(readiness("main", str(body), "maybe"), repo)
            self.assertEqual(2, invalid.returncode, invalid.stdout)
            self.assertIn("evidence kind must be", invalid.stderr)

    def test_binary_only_change_is_not_reported_as_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.make_repo(repo)
            binary = repo / "proof.png"
            binary.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
            self.assertEqual(0, run(["git", "add", "proof.png"], repo).returncode)
            self.assertEqual(
                0,
                run(["git", "-c", "commit.gpgsign=false", "commit", "-m", "add proof"], repo).returncode,
            )
            completed = run(readiness("main"), repo)
            self.assertNotIn("No changes detected", completed.stdout)

    def test_removed_secret_like_text_is_not_a_blocking_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.assertEqual(0, run(["git", "init", "-b", "main"], repo).returncode)
            self.assertEqual(0, run(["git", "config", "user.name", "Test User"], repo).returncode)
            self.assertEqual(0, run(["git", "config", "user.email", "test@example.com"], repo).returncode)
            config = repo / "config.txt"
            config.write_text('password = "leaked"\n', encoding="utf-8")
            self.assertEqual(0, run(["git", "add", "config.txt"], repo).returncode)
            self.assertEqual(0, run(["git", "-c", "commit.gpgsign=false", "commit", "-m", "base"], repo).returncode)
            self.assertEqual(0, run(["git", "checkout", "-b", "feature"], repo).returncode)
            config.write_text("password is loaded from the environment\n", encoding="utf-8")
            self.assertEqual(0, run(["git", "add", "config.txt"], repo).returncode)
            self.assertEqual(0, run(["git", "-c", "commit.gpgsign=false", "commit", "-m", "remove secret"], repo).returncode)
            completed = run(readiness("main"), repo)
            self.assertEqual(0, completed.returncode, completed.stdout)

    def test_debug_warning_does_not_echo_source_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.make_repo(repo, "worker.py")
            marker = "do-not-print-this-debug-value"
            (repo / "worker.py").write_text(f'print("{marker}")\n', encoding="utf-8")
            self.assertEqual(0, run(["git", "add", "worker.py"], repo).returncode)
            self.assertEqual(
                0,
                run(["git", "-c", "commit.gpgsign=false", "commit", "-m", "add debug"], repo).returncode,
            )
            completed = run(readiness("main"), repo)
            self.assertIn("Possible debug statements added", completed.stdout)
            self.assertNotIn(marker, completed.stdout)


if __name__ == "__main__":
    unittest.main()
