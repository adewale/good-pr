# good-pr

[![skills.sh](https://skills.sh/b/adewale/good-pr)](https://skills.sh/adewale/good-pr)

An Agent Skill that helps you craft pull requests maintainers actually want to merge.

## Origin

This project was inspired by a [tweet from @lukeparkerdev](https://x.com/lukeparkerdev/status/2032300518010470555) about the reality of community PRs in open source:

> the bottom line with community PRs are they are 99% of the time slop. even in the case that it looks like a good PR, there's suspicious things. this takes the team's time. we have to exactly repro the bug (because there's no steps in the issue/PR), there's a UI change with no before/after screenshots/video, there's terrible code, there's tests that don't test anything...

Rather than complain about bad PRs, we inverted every frustration into actionable guidance. The result is a skill that walks you through exactly what maintainers wish contributors would do.

## What It Does

The skill helps you prepare PRs by checking your work against the things that actually matter to reviewers:

1. **Reproduction steps** — Can a maintainer reproduce the bug from your description alone?
2. **Visual evidence** — Before/after screenshots or recordings for UI changes
3. **Code fit** — Does your code match the project's existing patterns?
4. **Meaningful tests** — Do your tests actually fail when the bug is reintroduced?
5. **Focused scope** — Is the diff minimal and limited to one concern?
6. **Standalone description** — Can a reviewer understand the change without pulling the code?
7. **Contributor trust** — Are you building a track record, or dropping a drive-by PR?

## Installation

Install with npx:

```bash
npx skills add adewale/good-pr
```

Skills appear on skills.sh automatically after users install the repo with the skills CLI. Install counts and leaderboard rankings come from anonymous CLI telemetry; opt out with `DISABLE_TELEMETRY=1`. The repo page customization in `skills.sh.json` is picked up after the repository is seen by telemetry and the cache refreshes.

## Agent compatibility

The installable skill directory is `skills/good-pr`. It uses the Agent Skills `SKILL.md` format and is configured for Codex, OpenCode, Pi, Gemini CLI, and Claude Code.

| Agent/client | Install or use |
|---|---|
| Codex | `cp -R skills/good-pr ~/.codex/skills/good-pr` |
| OpenCode | `cp -R skills/good-pr ~/.config/opencode/skills/good-pr` or use `.opencode/skills/good-pr` in a project |
| Pi | `pi install https://github.com/adewale/good-pr` or `pi --skill skills/good-pr` |
| Gemini CLI | `gemini skills install https://github.com/adewale/good-pr --path skills/good-pr` or copy to `.gemini/skills/good-pr` |
| Claude Code | `npx skills add adewale/good-pr` or copy to `.claude/skills/good-pr` |

Or install manually by copying the skill directory:

```bash
cp -r skills/good-pr ~/.claude/skills/good-pr
```

You can also reference it directly in your project's `.claude/settings.json`.

## Structure

```
skills/good-pr/
├── SKILL.md                      # Main skill instructions
├── references/
│   ├── pr-template.md            # Fill-in PR description template
│   ├── pr-example.md             # Filled-in PR description example
│   ├── review-checklist.md       # Self-review checklist before submitting
│   └── visual-evidence.md        # Screenshot policy, pitfalls, and examples
└── scripts/
    ├── check-pr-readiness.sh     # Automated PR hygiene checks
    └── check-visual-evidence.py  # PR Markdown evidence/provenance audit
```

Repository-only evidence lives outside the installable skill: `evidence/`
contains the dated PR-corpus receipt, while `evals/results/` contains the
source-bound model-eval proof bundle and sanitized outputs.

## Usage

Once installed, the skill activates when you ask your coding agent for help with pull requests:

- "Review my PR before I submit it"
- "Help me write a PR description for this diff"
- "I'm contributing to an open source project, check my changes"
- "Why do my PRs keep getting rejected?"

You can also run the readiness check script directly:

```bash
bash skills/good-pr/scripts/check-pr-readiness.sh main
```

Pass a drafted PR body as the second argument. Use the optional third argument
to override heuristic classification for generated output:

```bash
bash skills/good-pr/scripts/check-pr-readiness.sh main /tmp/pr-body.md
bash skills/good-pr/scripts/check-pr-readiness.sh main /tmp/pr-body.md generated
```

Or run the evidence audit directly. `ui` accepts proportionate hand-taken
screenshots; `generated` additionally checks the labelled claim/input/base/head
contract, a regeneration command or receipt, an associated oracle when
machine-checkable, and a material limitation:

```bash
python3 skills/good-pr/scripts/check-visual-evidence.py --kind ui /tmp/pr-body.md
python3 skills/good-pr/scripts/check-visual-evidence.py --kind generated --strict /tmp/pr-body.md
```

## Credits

- Original insight: [@lukeparkerdev](https://x.com/lukeparkerdev) — [tweet](https://x.com/lukeparkerdev/status/2032300518010470555)
- Skill implementation: Agent Skills-compatible instructions, tested across the shared skill eval harness

## License

MIT
