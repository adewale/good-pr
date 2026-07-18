#!/usr/bin/env python3
"""Run quick automated checks for common pull-request issues."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


PASS = "✓"
WARN = "⚠"
FAIL = "✗"
EVIDENCE_KINDS = {"auto", "ui", "generated", "none"}
TEST_FILE_RE = re.compile(r"test|spec|_test\.|\.test\.", re.IGNORECASE)
SECRET_RE = re.compile(
    r"(?:api[_-]?key|secret|password|token)\s*[:=]\s*[\"'][^\"']+",
    re.IGNORECASE,
)
DEBUG_RE = re.compile(
    r"console\.log|debugger|binding\.pry|import pdb|print\(", re.IGNORECASE
)
UI_FILE_RE = re.compile(r"\.(?:jsx|tsx|vue|svelte|css|scss|html|erb|astro|mdx)$", re.IGNORECASE)


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], check=False, capture_output=True, text=True
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout


def added_lines(diff: str) -> list[str]:
    return [
        line[1:]
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def text_line_count(numstat: str) -> int:
    total = 0
    for line in numstat.splitlines():
        parts = line.split("\t", 2)
        if len(parts) >= 2:
            total += sum(int(value) for value in parts[:2] if value.isdigit())
    return total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        usage="%(prog)s [base-branch] [pr-body-file] [auto|ui|generated|none]",
    )
    parser.add_argument("base", nargs="?", default="main")
    parser.add_argument("pr_body_file", nargs="?", default="")
    parser.add_argument("evidence_kind", nargs="?", default="auto")
    args = parser.parse_args()
    if args.evidence_kind not in EVIDENCE_KINDS:
        parser.error("evidence kind must be one of auto, ui, generated, or none")
    return args


def check_readiness(args: argparse.Namespace) -> int:
    comparison = f"{args.base}...HEAD"
    changed_files = [
        line for line in git("diff", comparison, "--name-only").splitlines() if line
    ]
    lines_changed = text_line_count(git("diff", comparison, "--numstat"))
    candidates = added_lines(git("diff", comparison, "-U0"))
    failures = 0

    print(f"PR Readiness Check (comparing against {args.base})")
    print("=============================================")
    print()

    if lines_changed > 500:
        print(f"{WARN}  Large diff: {lines_changed} lines changed. Consider splitting into smaller PRs.")
    elif lines_changed:
        print(f"{PASS}  Diff size: {lines_changed} lines changed")
    elif changed_files:
        print(f"{PASS}  Non-text or binary-only diff: {len(changed_files)} file(s) changed")
    else:
        print(f"{FAIL}  No changes detected against {args.base}")
        failures += 1

    test_files = sum(bool(TEST_FILE_RE.search(path)) for path in changed_files)
    if test_files:
        print(f"{PASS}  Test files modified: {test_files}")
    else:
        print(f"{WARN}  No test files modified. Does this change need tests?")

    try:
        commit_count = git("rev-list", "--count", f"{args.base}..HEAD").strip()
    except RuntimeError:
        commit_count = "0"
    print(f"{PASS}  Commits: {commit_count}")

    if any(SECRET_RE.search(line) for line in candidates):
        print(f"{WARN}  Possible secret assignment added; inspect the diff before publishing (value redacted)")
    else:
        print(f"{PASS}  No obvious secrets in diff")

    if any(DEBUG_RE.search(line) for line in candidates):
        print(f"{WARN}  Possible debug statements added; inspect the diff before publishing")
    else:
        print(f"{PASS}  No debug statements detected")

    ui_files = sum(bool(UI_FILE_RE.search(path)) for path in changed_files)
    if ui_files:
        print(
            f"{WARN}  {ui_files} UI-related files changed — include captioned "
            "before/after screenshots, or explain why pixels do not change"
        )
    else:
        print(f"{PASS}  No UI files changed")

    if args.pr_body_file:
        body_path = Path(args.pr_body_file)
        if not body_path.is_file():
            print(f"{FAIL}  PR body file does not exist: {body_path}")
            failures += 1
        else:
            evidence_args = ["--kind", args.evidence_kind]
            if args.evidence_kind == "auto" and ui_files:
                evidence_args.extend(["--fallback-kind", "ui"])
            evidence_args.extend(
                [
                    "--expected-base-sha",
                    git("merge-base", args.base, "HEAD").strip(),
                    "--expected-current-sha",
                    git("rev-parse", "HEAD").strip(),
                    str(body_path),
                ]
            )
            print()
            sys.stdout.flush()
            linter = Path(__file__).with_name("check-visual-evidence.py")
            completed = subprocess.run(
                [sys.executable, str(linter), *evidence_args], check=False
            )
            if completed.returncode:
                print(f"{FAIL}  Visual-evidence lint found blocking issues")
                failures += 1
            else:
                print(f"{PASS}  Visual-evidence lint completed")
    elif ui_files:
        print(f"{WARN}  Pass a PR body file as argument 2 to lint its visual evidence")

    print()
    print(f"Done. Address any {WARN} warnings and {FAIL} failures before submitting.")
    return 1 if failures else 0


def main() -> int:
    try:
        return check_readiness(parse_args())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
