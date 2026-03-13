#!/usr/bin/env node

import { existsSync, mkdirSync, cpSync, readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { homedir } from "os";

const __dirname = dirname(fileURLToPath(import.meta.url));
const packageRoot = join(__dirname, "..");
const skillSource = join(packageRoot, "good-pr");
const pkg = JSON.parse(readFileSync(join(packageRoot, "package.json"), "utf8"));

const skillsDir = join(homedir(), ".claude", "skills");
const skillDest = join(skillsDir, "good-pr");

console.log(`good-pr v${pkg.version}`);
console.log(`Installing skill to ${skillDest}...\n`);

// Create the skills directory if it doesn't exist
if (!existsSync(skillsDir)) {
  mkdirSync(skillsDir, { recursive: true });
}

// Copy skill files
cpSync(skillSource, skillDest, { recursive: true });

console.log("Installed files:");
console.log("  SKILL.md                        — Core skill instructions");
console.log("  references/pr-template.md       — PR description template");
console.log("  references/review-checklist.md  — Self-review checklist");
console.log("  scripts/check-pr-readiness.sh   — Automated PR hygiene checks");
console.log("");
console.log("Done! The good-pr skill is now available in Claude Code.");
console.log("");
console.log("Try it out:");
console.log('  "Review my PR before I submit it"');
console.log('  "Help me write a PR description for this diff"');
console.log('  "I\'m contributing to an open source project, check my changes"');
