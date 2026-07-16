#!/usr/bin/env python3
"""Audit the visual-evidence section of a pull request description.

The checker is deliberately dependency-free. It reviews Markdown structure and
evidence provenance; it does not download images or judge their pixels.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse


VISUAL_HEADING_RE = re.compile(
    r"^(#{2,6})\s+(?:visual(?:\s+evidence|s)?|screenshots?"
    r"(?:\s*/\s*recordings?)?|recordings?)(?:\s*/[^\n]+)?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
ANY_HEADING_RE = re.compile(r"^(#{1,6})\s+.+$", re.MULTILINE)
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+[^)]*)?\)")
REFERENCE_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\[([^\]]+)\]")
REFERENCE_DEFINITION_RE = re.compile(
    r"^[ \t]{0,3}\[([^\]]+)\]:[ \t]*(?:<([^>]+)>|(\S+))(?:[ \t]+[^\n]+)?$",
    re.MULTILINE,
)
ATTACHMENT_URL_PATTERN = r"https://github\.com/user-attachments/assets/[A-Za-z0-9-]+"
MARKDOWN_ATTACHMENT_LINK_RE = re.compile(
    rf"(?<!!)\[([^\]]+)\]\(({ATTACHMENT_URL_PATTERN})\)",
    re.IGNORECASE,
)
BARE_ATTACHMENT_RE = re.compile(ATTACHMENT_URL_PATTERN, re.IGNORECASE)
HTML_MEDIA_RE = re.compile(r"<(img|video)\b([^>]*)>", re.IGNORECASE)
HTML_ATTRIBUTE_RE = re.compile(r"([:\w-]+)\s*=\s*([\"'])(.*?)\2", re.DOTALL)
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"(`+)(.*?)\1", re.DOTALL)
BASELINE_SHA_RE = re.compile(
    r"\b(?:base|baseline)(?:\s+(?:commit|sha))?\s*(?::|=|is|at)?\s*`?([0-9a-f]{7,40})`?\b",
    re.IGNORECASE,
)
CURRENT_SHA_RE = re.compile(
    r"\b(?:current|head)(?:\s+(?:commit|sha))?\s*(?::|=|is|at)?\s*`?([0-9a-f]{7,40})`?\b",
    re.IGNORECASE,
)

NO_VISUAL_IMPACT_RE = re.compile(
    r"\b(?:no (?:visible|visual) change|nothing visually perceptible|"
    r"does not change (?:the )?pixels|"
    r"not applicable[^\n]{0,100}(?:no visual|because))\b",
    re.IGNORECASE,
)
NO_UI_IMPACT_RE = re.compile(
    r"\b(?:no ui change|does not change (?:the )?ui)\b",
    re.IGNORECASE,
)
NO_RENDERED_IMPACT_RE = re.compile(
    r"\b(?:no (?:rendered[- ]output|page geometry) change|"
    r"does not change (?:the )?(?:rendered output|page geometry))\b",
    re.IGNORECASE,
)
NO_BASELINE_RE = re.compile(
    r"\b(?:did not exist|no (?:existing|prior|previous|renderable) "
    r"(?:baseline|surface|ui|render|output)|unsupported (?:header|syntax)|"
    r"produced no renderable output|nothing to capture)\b",
    re.IGNORECASE,
)
REGENERATION_COMMAND_RE = re.compile(
    r"^\s*(?:\*\*)?(?:regenerate|reproduce)(?:\*\*)?(?:\s+with)?\s*:?\s*"
    r"(?:`(?:bun|npm|pnpm|yarn|python3?|make|cargo|go|bash|sh|\.\/)[^`\n]+`|"
    r"(?:bun|npm|pnpm|yarn|python3?|make|cargo|go|bash|sh|\.\/)\s+\S+)",
    re.IGNORECASE | re.MULTILINE,
)
RECEIPT_RE = re.compile(
    r"^\s*(?:\*\*)?(?:generated\s+)?receipt(?:\*\*)?\s*:\s*[^\n]*"
    r"(?:sha-?256|checksum|hash)",
    re.IGNORECASE | re.MULTILINE,
)
CLAIM_RE = re.compile(
    r"^\s*(?:\*\*)?claim(?:\*\*)?\s*:\s*\S.+$", re.IGNORECASE | re.MULTILINE
)
INPUT_RE = re.compile(
    r"^\s*(?:\*\*)?(?:input|fixture|input\s*/\s*fixture)(?:\*\*)?\s*:\s*\S.+$",
    re.IGNORECASE | re.MULTILINE,
)
LIMITATION_RE = re.compile(
    r"^\s*(?:\*\*)?(?:limitation|what (?:this )?(?:image|evidence) cannot prove)"
    r"(?:\*\*)?\s*:\s*\S.+$",
    re.IGNORECASE | re.MULTILINE,
)
INDEPENDENT_CHECK_RE = re.compile(
    r"^\s*(?:\*\*)?(?:independent (?:check|oracle)|metric|invariant)(?:\*\*)?\s*:\s*\S.+$",
    re.IGNORECASE | re.MULTILINE,
)
NO_ORACLE_NEEDED_RE = re.compile(
    r"\b(?:subjective|not machine-checkable|no objective metric|"
    r"(?:metric|automated check) would be misleading)\b",
    re.IGNORECASE,
)
REVIEW_CUE_RE = re.compile(
    r"\b(?:what to (?:inspect|look for|check)|inspect:|reviewer should (?:inspect|check))\b",
    re.IGNORECASE,
)
GENERATOR_SIGNAL_RE = re.compile(
    r"\b(?:generated (?:artifacts?|outputs?|images?|charts?|diagrams?|pdfs?)|contact sheet|"
    r"baseline commit|evidence generator|(?:image|pdf|chart|diagram|svg) (?:renderer|pipeline)|"
    r"(?:rendered|renderer) (?:artifact|output|image|chart|diagram|pdf)|charting|diagramming|"
    r"mermaid|svg output|canvas output)\b",
    re.IGNORECASE,
)
ORACLE_RE = re.compile(
    r"\b(?:geometry assertion|regression test|unit test|integration test|"
    r"snapshot test|metric (?:gate|check|threshold)|freshness (?:gate|check)|"
    r"hash(?:ed|es|ing)?|checksum|positive control|negative control)\b",
    re.IGNORECASE,
)
MALFORMED_URL_RE = re.compile(r"\(\s*``https?://|https?://[^\s)]+``\s*\)", re.IGNORECASE)


@dataclass(frozen=True)
class Media:
    alt: str
    url: str
    source: str


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str


def read_body(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"cannot read PR body {path!r}: {exc}") from exc


def preserve_newlines(match: re.Match[str]) -> str:
    return "\n" * match.group(0).count("\n")


def strip_html_comments(text: str) -> str:
    """Remove closed and unclosed HTML comments while preserving line structure."""
    output: list[str] = []
    cursor = 0
    while True:
        start = text.find("<!--", cursor)
        if start < 0:
            output.append(text[cursor:])
            break
        output.append(text[cursor:start])
        end = text.find("-->", start + 4)
        if end < 0:
            hidden = text[start:]
            output.append("\n" * hidden.count("\n"))
            break
        hidden = text[start : end + 3]
        output.append("\n" * hidden.count("\n"))
        cursor = end + 3
    return "".join(output)


def strip_fenced_code(text: str) -> str:
    """Remove fenced and four-space-indented code that GitHub does not render as media."""
    output: list[str] = []
    fence_char = ""
    fence_length = 0
    for line in text.splitlines(keepends=True):
        match = FENCE_RE.match(line)
        if not fence_char and match:
            marker = match.group(1)
            fence_char = marker[0]
            fence_length = len(marker)
            output.append("\n" if line.endswith("\n") else "")
            continue
        if fence_char:
            if match:
                marker = match.group(1)
                if marker[0] == fence_char and len(marker) >= fence_length:
                    fence_char = ""
                    fence_length = 0
            output.append("\n" if line.endswith("\n") else "")
            continue
        if line.startswith("    ") or line.startswith("\t"):
            output.append("\n" if line.endswith("\n") else "")
        else:
            output.append(line)
    return "".join(output)


def strip_inline_code(text: str) -> str:
    """Remove inline examples so image-looking code is not counted as media."""
    return INLINE_CODE_RE.sub(lambda match: " " * len(match.group(0)), text)


def semantic_markdown(text: str) -> str:
    return strip_fenced_code(strip_html_comments(text))


def visual_sections(body: str) -> list[str]:
    sections: list[str] = []
    headings = list(ANY_HEADING_RE.finditer(body))
    for index, heading in enumerate(headings):
        if not VISUAL_HEADING_RE.fullmatch(heading.group(0)):
            continue
        level = len(heading.group(1))
        end = len(body)
        for later in headings[index + 1 :]:
            if len(later.group(1)) <= level:
                end = later.start()
                break
        sections.append(body[heading.start() : end].strip())
    return sections


def extract_media(text: str) -> list[Media]:
    media = [
        Media(alt=match.group(1).strip(), url=match.group(2).strip(), source="markdown")
        for match in MARKDOWN_IMAGE_RE.finditer(text)
    ]
    definitions = {
        match.group(1).strip().casefold(): (match.group(2) or match.group(3)).strip()
        for match in REFERENCE_DEFINITION_RE.finditer(text)
    }
    known_urls = {item.url for item in media}
    for match in REFERENCE_IMAGE_RE.finditer(text):
        url = definitions.get(match.group(2).strip().casefold())
        if url and url not in known_urls:
            media.append(Media(alt=match.group(1).strip(), url=url, source="reference"))
            known_urls.add(url)
    for match in HTML_MEDIA_RE.finditer(text):
        attributes = {
            key.casefold(): value.strip()
            for key, _, value in HTML_ATTRIBUTE_RE.findall(match.group(2))
        }
        url = attributes.get("src", "")
        if url:
            media.append(
                Media(
                    alt=attributes.get("alt", attributes.get("aria-label", "")),
                    url=url,
                    source=match.group(1).casefold(),
                )
            )
    known_urls = {item.url for item in media}
    for match in MARKDOWN_ATTACHMENT_LINK_RE.finditer(text):
        url = match.group(2)
        if url not in known_urls:
            media.append(Media(alt=match.group(1).strip(), url=url, source="attachment"))
            known_urls.add(url)
    for match in BARE_ATTACHMENT_RE.finditer(text):
        url = match.group(0)
        if url not in known_urls:
            media.append(Media(alt="", url=url, source="attachment"))
            known_urls.add(url)
    return media


def github_ref(url: str) -> tuple[bool, str | None]:
    """Return whether URL is repository-hosted and its ref, when identifiable."""
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    host = parsed.netloc.casefold()
    if host == "raw.githubusercontent.com" and len(parts) >= 3:
        return True, parts[2]
    if host == "github.com" and len(parts) >= 5 and parts[2] in {"blob", "raw"}:
        return True, parts[3]
    if not parsed.scheme and not parsed.netloc:
        return True, None
    return False, None


def meaningful_alt(alt: str) -> bool:
    normalized = re.sub(r"\s+", " ", alt).strip().casefold()
    return len(normalized) >= 6 and normalized not in {
        "before",
        "after",
        "image",
        "screenshot",
        "visual evidence",
    }


def same_commit_ref(left: str, right: str) -> bool:
    """Treat abbreviated and full hexadecimal names of one commit as equal."""
    left = left.casefold()
    right = right.casefold()
    return left.startswith(right) or right.startswith(left)


def infer_kind(body: str, section_text: str, media: list[Media], fallback_kind: str) -> str:
    if GENERATOR_SIGNAL_RE.search(body):
        return "generated"
    if section_text or media:
        return "ui"
    return fallback_kind


def audit(
    body: str,
    requested_kind: str,
    fallback_kind: str = "none",
    *,
    expected_base_sha: str | None = None,
    expected_current_sha: str | None = None,
) -> dict:
    semantic_body = semantic_markdown(body)
    sections = visual_sections(semantic_body)
    section_text = "\n\n".join(sections)
    evidence_text = section_text or semantic_body
    media = extract_media(strip_inline_code(evidence_text))
    has_evidence_receipt = bool(RECEIPT_RE.search(evidence_text))
    kind = (
        infer_kind(semantic_body, section_text, media, fallback_kind)
        if requested_kind == "auto"
        else requested_kind
    )
    findings: list[Finding] = []

    def add(level: str, code: str, message: str) -> None:
        findings.append(Finding(level=level, code=code, message=message))

    general_no_impact = bool(NO_VISUAL_IMPACT_RE.search(evidence_text))
    if kind == "generated":
        no_impact = general_no_impact or bool(NO_RENDERED_IMPACT_RE.search(evidence_text))
    elif kind == "ui":
        no_impact = general_no_impact or bool(
            NO_UI_IMPACT_RE.search(evidence_text) or NO_RENDERED_IMPACT_RE.search(evidence_text)
        )
    else:
        no_impact = general_no_impact
    contradiction = bool(
        no_impact
        and re.search(
            r"\b(?:but|however|except|although)\b[^\n]{0,160}\b(?:changes?|changed|different|visible)\b",
            evidence_text,
            re.IGNORECASE,
        )
    )
    if contradiction:
        no_impact = False
        add(
            "error",
            "contradictory-no-impact",
            "The no-impact statement is qualified by a visible change; provide visual evidence or remove the contradiction.",
        )
    no_baseline = bool(NO_BASELINE_RE.search(evidence_text))
    required = kind in {"ui", "generated"} and not no_impact

    if required:
        if sections:
            add("pass", "visual-section", "Dedicated visual-evidence section found.")
        else:
            add("error", "visual-section", "Add a dedicated Visual evidence or Screenshots section.")
        if media:
            add("pass", "visual-assets", f"Found {len(media)} embedded visual asset(s).")
        else:
            add("error", "visual-assets", "Embed at least one screenshot, recording, or rendered artifact.")
    elif no_impact:
        add("pass", "no-visual-impact", "Explicit explanation says why visual evidence is not applicable.")

    if required and media:
        has_before = bool(re.search(r"\bbefore\b", evidence_text, re.IGNORECASE))
        has_after = bool(re.search(r"\bafter\b", evidence_text, re.IGNORECASE))
        has_recording = any(item.source in {"video", "attachment"} for item in media)
        has_comparison = has_before and has_after and (len(media) >= 2 or has_recording)
        has_honest_after = no_baseline and has_after
        if has_comparison or has_honest_after:
            message = "Before/after comparison found."
            if has_honest_after and not has_comparison:
                message = "After evidence found with an explicit explanation that no honest baseline exists."
            add("pass", "causal-comparison", message)
        else:
            add(
                "error",
                "causal-comparison",
                "Show before and after, or explain why no honest visual baseline exists.",
            )

    missing_alt = [item.url for item in media if not meaningful_alt(item.alt)]
    if media and missing_alt:
        add(
            "warning",
            "alt-text",
            f"{len(missing_alt)} asset(s) have missing or generic alt/link text; describe the visible claim.",
        )
    elif media:
        add("pass", "alt-text", "Every embedded asset has descriptive alt text.")

    if MALFORMED_URL_RE.search(evidence_text):
        add("error", "markdown-image-url", "An image URL is wrapped in doubled backticks and may not render.")

    unpinned: list[str] = []
    uploaded_generated: list[str] = []
    external_generated: list[str] = []
    repository_hosted_count = 0
    for item in media:
        repository_hosted, ref = github_ref(item.url)
        if repository_hosted:
            repository_hosted_count += 1
            if ref is None or not FULL_SHA_RE.fullmatch(ref):
                unpinned.append(item.url)
        elif kind == "generated" and urlparse(item.url).netloc.casefold() in {
            "github.com",
            "user-images.githubusercontent.com",
            "private-user-images.githubusercontent.com",
        } and not repository_hosted:
            uploaded_generated.append(item.url)
        elif kind == "generated" and urlparse(item.url).scheme in {"http", "https"}:
            external_generated.append(item.url)

    if repository_hosted_count and not unpinned:
        add("pass", "immutable-urls", "Repository-hosted evidence URLs are pinned to full commit SHAs.")
    elif unpinned:
        level = "error" if kind == "generated" else "warning"
        add(
            level,
            "immutable-urls",
            f"{len(unpinned)} repository-hosted asset(s) use a mutable or relative ref; pin generated evidence to a full commit SHA.",
        )
    if uploaded_generated:
        add(
            "warning",
            "generated-upload-provenance",
            f"{len(uploaded_generated)} generated asset(s) are uploaded attachments; commit them and use SHA-pinned URLs when practical.",
        )
    if external_generated:
        if has_evidence_receipt:
            add(
                "pass",
                "external-url-provenance",
                "External generated assets are accompanied by a labelled content-hash receipt.",
            )
        else:
            add(
                "warning",
                "external-url-provenance",
                f"{len(external_generated)} generated asset(s) use external URLs whose immutability was not verified; provide a content-addressed receipt or commit-pinned evidence.",
            )

    if kind == "generated" and required:
        claim_match = CLAIM_RE.search(evidence_text)
        first_media_position = min(
            (evidence_text.find(item.url) for item in media if evidence_text.find(item.url) >= 0),
            default=len(evidence_text),
        )
        if claim_match and claim_match.start() < first_media_position:
            add("pass", "visible-claim", "A specific visible claim is stated before the evidence.")
        else:
            add("error", "visible-claim", "State one labelled `Claim:` before the generated visual evidence.")

        if INPUT_RE.search(evidence_text):
            add("pass", "same-input", "A named input or fixture binds the before/after comparison.")
        else:
            add("error", "same-input", "Name the identical input/fixture and configuration used at both revisions.")

        has_regeneration = bool(REGENERATION_COMMAND_RE.search(evidence_text))
        has_receipt = has_evidence_receipt
        if has_regeneration:
            add("pass", "regeneration-command", "A regeneration or reproduction command is documented.")
        elif has_receipt:
            add("pass", "evidence-receipt", "A labelled generated receipt records content hashes.")
        else:
            add(
                "error",
                "regeneration-command",
                "Document a labelled `Regenerate:` command or a generated `Receipt:` with content hashes.",
            )
        baseline_match = BASELINE_SHA_RE.search(evidence_text)
        current_match = CURRENT_SHA_RE.search(evidence_text)
        same_revision = bool(
            baseline_match
            and current_match
            and same_commit_ref(baseline_match.group(1), current_match.group(1))
        )
        baseline_mismatch = bool(
            baseline_match
            and expected_base_sha
            and not same_commit_ref(baseline_match.group(1), expected_base_sha)
        )
        if baseline_mismatch:
            add(
                "error",
                "baseline-provenance",
                "The labelled baseline SHA does not match the repository merge-base supplied by the readiness wrapper.",
            )
        elif no_baseline:
            add("pass", "baseline-provenance", "The baseline is immutable or its honest absence is explained.")
        elif baseline_match and not same_revision:
            add("pass", "baseline-provenance", "An explicitly labelled baseline commit is documented.")
        elif same_revision:
            add(
                "error",
                "baseline-provenance",
                "The labelled baseline and current commits must identify different revisions.",
            )
        else:
            add(
                "error",
                "baseline-provenance",
                "Name the immutable base/baseline commit used for the before render.",
            )
        current_mismatch = bool(
            current_match
            and expected_current_sha
            and not same_commit_ref(current_match.group(1), expected_current_sha)
        )
        if not current_match:
            add("error", "current-provenance", "Name the immutable current/head SHA used for the after render.")
        elif current_mismatch:
            add(
                "error",
                "current-provenance",
                "The labelled current/head SHA does not match the checked-out HEAD supplied by the readiness wrapper.",
            )
        elif not same_revision:
            add("pass", "current-provenance", "An explicitly labelled current/head commit is documented.")
        if REVIEW_CUE_RE.search(evidence_text):
            add("pass", "review-cue", "The description tells reviewers what to inspect.")
        else:
            add(
                "warning",
                "review-cue",
                "Add a concise “What to inspect” cue so reviewers can verify a specific pixel claim.",
            )
        independent_match = INDEPENDENT_CHECK_RE.search(evidence_text)
        if independent_match and (
            ORACLE_RE.search(independent_match.group(0))
            or "`" in independent_match.group(0)
            or "](" in independent_match.group(0)
        ):
            add("pass", "independent-oracle", "A labelled independent test, metric, control, or freshness check is named.")
        elif LIMITATION_RE.search(evidence_text) and NO_ORACLE_NEEDED_RE.search(evidence_text):
            add(
                "pass",
                "independent-oracle",
                "The limitation proportionately explains why no machine-checkable oracle applies.",
            )
        else:
            add(
                "warning",
                "independent-oracle",
                "Add a labelled `Independent check:` tied to the claim, or explain under `Limitation:` why no machine-checkable oracle is proportionate.",
            )
        if LIMITATION_RE.search(evidence_text):
            add("pass", "evidence-limitation", "The description states what the visual evidence cannot prove.")
        else:
            add(
                "warning",
                "evidence-limitation",
                "Add a labelled `Limitation:` stating the material boundary of the visual evidence.",
            )

    if len(media) > 12:
        add(
            "warning",
            "evidence-volume",
            f"{len(media)} assets are embedded; prefer a contact sheet plus links to exhaustive evidence.",
        )

    errors = sum(item.level == "error" for item in findings)
    warnings = sum(item.level == "warning" for item in findings)
    status = "fail" if errors else "warn" if warnings else "pass"
    return {
        "status": status,
        "kind": kind,
        "media_count": len(media),
        "errors": errors,
        "warnings": warnings,
        "findings": [asdict(item) for item in findings],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "body_file",
        nargs="?",
        default="-",
        help="PR description Markdown file; omit or use - to read stdin",
    )
    parser.add_argument(
        "--kind",
        choices=("auto", "ui", "generated", "none"),
        default="auto",
        help="evidence policy to apply (default: infer from the description)",
    )
    parser.add_argument(
        "--fallback-kind",
        choices=("ui", "none"),
        default="none",
        help="policy used when auto mode finds no signal (default: none)",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--expected-base-sha", help="merge-base SHA to compare with a labelled baseline")
    parser.add_argument("--expected-current-sha", help="checked-out HEAD SHA to compare with a labelled current revision")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return non-zero for warnings as well as errors",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = audit(
        read_body(args.body_file),
        args.kind,
        args.fallback_kind,
        expected_base_sha=args.expected_base_sha,
        expected_current_sha=args.expected_current_sha,
    )
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Visual Evidence Audit ({result['kind']})")
        print("=" * 32)
        symbols = {"pass": "✓", "warning": "⚠", "error": "✗"}
        for finding in result["findings"]:
            print(f"{symbols[finding['level']]}  {finding['code']}: {finding['message']}")
        if not result["findings"]:
            print("✓  No visual-evidence requirements apply.")
        print(
            f"\nResult: {result['status'].upper()} "
            f"({result['errors']} error(s), {result['warnings']} warning(s))"
        )
    if result["errors"]:
        return 1
    if args.strict and result["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
