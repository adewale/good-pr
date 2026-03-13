# good-pr

A Claude Code skill that helps you craft pull requests maintainers actually want to merge.

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

Or install manually by copying the skill directory:

```bash
cp -r good-pr/ ~/.claude/skills/good-pr
```

You can also reference it directly in your project's `.claude/settings.json`.

## Structure

```
good-pr/
├── SKILL.md                      # Main skill instructions
├── references/
│   ├── pr-template.md            # Fill-in PR description template
│   └── review-checklist.md       # Self-review checklist before submitting
└── scripts/
    └── check-pr-readiness.sh     # Automated PR hygiene checks
```

## Usage

Once installed, the skill activates when you ask Claude Code for help with pull requests:

- "Review my PR before I submit it"
- "Help me write a PR description for this diff"
- "I'm contributing to an open source project, check my changes"
- "Why do my PRs keep getting rejected?"

You can also run the readiness check script directly:

```bash
bash good-pr/scripts/check-pr-readiness.sh main
```

## Credits

- Original insight: [@lukeparkerdev](https://x.com/lukeparkerdev) — [tweet](https://x.com/lukeparkerdev/status/2032300518010470555)
- Skill implementation: Built with [Claude Code](https://claude.ai/claude-code)

## License

MIT
