#!/usr/bin/env python3
"""Summarize visual-evidence practices across a GitHub author's PR corpus."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from urllib.parse import urlparse


FIELDS = "number,title,url,repository,body,createdAt,state"
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+[^)]*)?\)")
HTML_IMAGE_RE = re.compile(r"<img\b([^>]*)>", re.IGNORECASE)
HTML_ATTRIBUTE_RE = re.compile(r"([:\w-]+)\s*=\s*([\"'])(.*?)\2", re.DOTALL)
HEADING_RE = re.compile(r"^#{2,6}\s+(.+?)\s*$", re.MULTILINE)
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
HTML_COMMENT_RE = re.compile(r"<!--[\s\S]*?-->")
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"(`+)([^`\n]*?)\1")


def preserve_newlines(match: re.Match[str]) -> str:
    return "\n" * match.group(0).count("\n")


def strip_nonrendered_markdown(text: str, *, strip_inline: bool = True) -> str:
    text = HTML_COMMENT_RE.sub(preserve_newlines, text)
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
        output.append(line)
    rendered = "".join(output)
    if strip_inline:
        return INLINE_CODE_RE.sub(lambda match: " " * len(match.group(0)), rendered)
    return rendered


def extract_images(body: str) -> list[tuple[str, str]]:
    body = strip_nonrendered_markdown(body)
    result = [
        (match.group(1).strip(), match.group(2).strip())
        for match in MARKDOWN_IMAGE_RE.finditer(body)
    ]
    for match in HTML_IMAGE_RE.finditer(body):
        attributes = {
            key.casefold(): value.strip()
            for key, _, value in HTML_ATTRIBUTE_RE.findall(match.group(1))
        }
        if attributes.get("src"):
            result.append((attributes.get("alt", ""), attributes["src"]))
    return result


def repository_ref(url: str) -> tuple[bool, str | None]:
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


def normalize_headings(body: str) -> set[str]:
    return {
        re.sub(r"[^a-z]+", " ", heading.casefold()).strip()
        for heading in HEADING_RE.findall(body)
    }


def analyze(prs: list[dict], author: str, limit: int = 1000) -> dict:
    rows: list[dict] = []
    for pr in prs:
        source_body = pr.get("body") or ""
        body = strip_nonrendered_markdown(source_body, strip_inline=False)
        media = extract_images(source_body)
        headings = normalize_headings(body)
        refs = [repository_ref(url) for _, url in media]
        pinned = sum(hosted and ref is not None and FULL_SHA_RE.fullmatch(ref) is not None for hosted, ref in refs)
        mutable = sum(hosted and (ref is None or FULL_SHA_RE.fullmatch(ref) is None) for hosted, ref in refs)
        visual_heading = any(re.search(r"visual|screenshot|recording", heading) for heading in headings)
        before_after = bool(re.search(r"\bbefore\b", body, re.IGNORECASE) and re.search(r"\bafter\b", body, re.IGNORECASE))
        regeneration = bool(re.search(r"\b(?:regenerat\w*|reproduc\w*)\b", body, re.IGNORECASE))
        review_cue = bool(re.search(r"what to (?:inspect|look for|check)|\binspect:", body, re.IGNORECASE))
        no_screenshot = bool(re.search(
            r"screenshots?[\s\S]{0,180}(?:not applicable|nothing visually perceptible|"
            r"no page geometry changed|no rendered-output change|no visual change)",
            body,
            re.IGNORECASE,
        ))
        receipt = bool(re.search(r"\b(?:sha-?256|receipt|byte-identical|hash(?:ed|es)?)\b", body, re.IGNORECASE))
        score = (
            2 * bool(media)
            + 2 * visual_heading
            + 2 * before_after
            + 2 * regeneration
            + 2 * bool(pinned)
            + 2 * review_cue
            + int("contact sheet" in body.casefold())
            + int(receipt)
        )
        repository = pr["repository"]["nameWithOwner"]
        rows.append({
            "repository": repository,
            "number": pr["number"],
            "title": pr["title"],
            "url": pr["url"],
            "created_at": pr["createdAt"],
            "self_owned": repository.startswith(f"{author}/"),
            "images": len(media),
            "visual_heading": visual_heading,
            "before_after": before_after,
            "regeneration": regeneration,
            "pinned_images": pinned,
            "mutable_images": mutable,
            "weak_alt": sum(len(re.sub(r"\s+", " ", alt).strip()) < 6 for alt, _ in media),
            "review_cue": review_cue,
            "contact_sheet": "contact sheet" in body.casefold(),
            "receipt": receipt,
            "no_screenshot_rationale": no_screenshot,
            "malformed_image_url": bool(re.search(r"\(\s*``https?://|https?://[^\s)]+``\s*\)", body, re.IGNORECASE)),
            "score": score,
        })

    visual = [row for row in rows if row["images"]]
    repositories = Counter(row["repository"] for row in rows)
    return {
        "method": {
            "query": f"gh search prs --author {author} --limit {limit}",
            "note": "Rendered-Markdown-oriented PR-description analysis; images are not downloaded or judged.",
            "search_limit_reached": len(prs) >= limit,
        },
        "total_authored_prs": len(rows),
        "self_owned_repo_prs": sum(row["self_owned"] for row in rows),
        "external_repo_prs": sum(not row["self_owned"] for row in rows),
        "repositories": len(repositories),
        "prs_with_images": len(visual),
        "total_embedded_images": sum(row["images"] for row in visual),
        "image_prs_before_after": sum(row["before_after"] for row in visual),
        "image_prs_regeneration": sum(row["regeneration"] for row in visual),
        "image_prs_sha_pinned": sum(bool(row["pinned_images"]) for row in visual),
        "sha_pinned_images": sum(row["pinned_images"] for row in visual),
        "mutable_repo_image_urls": sum(row["mutable_images"] for row in visual),
        "images_missing_or_short_alt": sum(row["weak_alt"] for row in visual),
        "image_prs_review_cue": sum(row["review_cue"] for row in visual),
        "image_prs_contact_sheet": sum(row["contact_sheet"] for row in visual),
        "image_prs_receipts_or_hashes": sum(row["receipt"] for row in visual),
        "explicit_no_screenshot_rationales": sum(row["no_screenshot_rationale"] for row in rows),
        "malformed_double_tick_image_urls": sum(row["malformed_image_url"] for row in rows),
        "top_repositories": repositories.most_common(20),
        "top_visual_exemplars": sorted(
            visual,
            key=lambda row: (row["score"], row["created_at"]),
            reverse=True,
        )[:20],
    }


def fetch_prs(author: str, limit: int) -> list[dict]:
    command = [
        "gh",
        "search",
        "prs",
        "--author",
        author,
        "--limit",
        str(limit),
        "--json",
        FIELDS,
    ]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise SystemExit("cannot run corpus search: GitHub CLI (`gh`) is not installed") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or f"gh exited with status {exc.returncode}"
        raise SystemExit(f"cannot run corpus search: {detail}") from exc
    return json.loads(completed.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author", required=True, help="GitHub login whose authored PRs should be searched")
    parser.add_argument("--limit", type=int, default=1000, help="GitHub search result limit (default: 1000)")
    args = parser.parse_args()
    print(json.dumps(analyze(fetch_prs(args.author, args.limit), args.author, args.limit), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
