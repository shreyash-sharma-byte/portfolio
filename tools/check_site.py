#!/usr/bin/env python3
"""Content and integrity checker for the portfolio site.

Enforces the standing rules that are easy to break by accident and invisible in a
browser: the exact footer credit on every page, no emoji anywhere in the UI, no
marketing language, no claim the source repositories contradict, working image
and link targets, and a page skeleton that is complete (title, description,
lang, skip link, exactly one h1).

Usage:
    python3 tools/check_site.py [site-dir]
Exit status is 1 if any check fails.

Standard library only.
"""

from __future__ import annotations

import html
import re
import sys
import unicodedata
from pathlib import Path

# Characters that count as emoji or UI glyphs. Typographic characters the site
# legitimately uses — the middle dot, en/em dashes, the arrow — are deliberately
# outside these ranges.
EMOJI_RANGES = (
    (0x1F000, 0x1FAFF),   # pictographs, emoticons, symbols
    (0x2600, 0x27BF),     # miscellaneous symbols, dingbats, check marks
    (0x2B00, 0x2BFF),     # additional arrows and symbols
    (0x25A0, 0x25FF),     # geometric shapes (play, target, grid glyphs)
    (0xFE0F, 0xFE0F),     # variation selector, forces emoji presentation
    (0x2190, 0x21FF),     # arrows — only flagged inside a glyph context below
)

# The arrow is allowed as typography; the rest of the arrow block is not used.
ALLOWED_GLYPHS = {"\u2190", "\u2192", "\u00b7", "\u2013", "\u2014", "\u00d7", "\u2264", "\u2265"}

# Language the design standard bans outright, plus filler that should never ship.
GLOBAL_PHRASES = (
    "seamless", "cutting-edge", "cutting edge", "revolutionary", "passionate",
    "powerful", "robust", "leverage", "blazing", "world-class", "best-in-class",
    "state-of-the-art", "game-chang", "unlock the power", "supercharge",
    # a test count the last CI run contradicts
    "299/299",
    # filler
    "lorem ipsum", "placeholder",
)

# Phrases that are only wrong on a specific page, because elsewhere they name a
# real mechanism. ClaimShield's per-address allowance must never be called a
# rate limit or a free tier; the claims platform genuinely does rate-limit filings.
SCOPED_PHRASES: dict[str, tuple[str, ...]] = {
    "claimshield.html": ("free tier", "rate limit", "multi-agent", "multi agent"),
}

# Pages allowed to contain a phrase because the page exists to explain its absence.
PHRASE_ALLOWLIST: dict[str, set[str]] = {
    # the ClaimShield page must be able to say what is NOT built
    "claimshield.html": {"multi-agent", "multi agent"},
}

# Short words checked on word boundaries so they cannot match inside other words.
WORD_PHRASES = ("todo", "tbd", "xxx", "fixme")

FOOTER_REQUIRED = (
    "Made by",
    "https://github.com/shreyash-sharma-byte",
    "https://www.linkedin.com/in/shreyash-sharma-908b741a9",
    "mailto:shreyashms2501@gmail.com",
)

REQUIRED_HEAD = (
    '<!doctype html>',
    'lang="en"',
    'name="viewport"',
    "<title>",
    'name="description"',
    'rel="stylesheet"',
)

IMG_ATTRS = ("alt=", "width=", "height=", 'loading="lazy"')


def strip_tags(src: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", src, flags=re.S | re.I)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(text)


def find_emoji(text: str) -> list[tuple[str, str]]:
    hits = []
    for ch in text:
        if ch in ALLOWED_GLYPHS:
            continue
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in EMOJI_RANGES):
            name = unicodedata.name(ch, "UNKNOWN")
            hits.append((ch, name))
    return hits


def check_page(path: Path, site: Path) -> tuple[list[str], list[str]]:
    """Return (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []
    src = path.read_text(encoding="utf-8")
    text = strip_tags(src)

    for needle in REQUIRED_HEAD:
        if needle not in src:
            errors.append(f"missing from <head>: {needle}")

    if src.count("<h1") != 1:
        errors.append(f"expected exactly one <h1>, found {src.count('<h1')}")

    if 'class="skip"' not in src:
        errors.append("no skip link")

    for needle in FOOTER_REQUIRED:
        if needle not in src:
            errors.append(f"footer missing: {needle}")

    # JSON-LD is data, not script: it does not execute and loads nothing.
    executable = [t for t in re.findall(r"<script\b[^>]*>", src, re.I)
                  if "ld+json" not in t]
    if executable:
        warnings.append("page contains a <script> tag; the site is otherwise JavaScript-free")

    # Emoji in visible text or in markup.
    for ch, name in find_emoji(src):
        errors.append(f"emoji/glyph present: {ch!r} ({name})")

    # Marketing language, contradicted claims and filler.
    lowered = text.lower()
    allowed = PHRASE_ALLOWLIST.get(path.name, set())
    phrases = list(GLOBAL_PHRASES) + list(SCOPED_PHRASES.get(path.name, ()))
    for phrase in phrases:
        if phrase in allowed:
            continue
        if phrase in lowered:
            errors.append(f"forbidden phrase in visible text: {phrase!r}")
    for word in WORD_PHRASES:
        if re.search(rf"\b{word}\b", lowered):
            errors.append(f"unfinished-work marker in visible text: {word!r}")

    # Images resolve and carry accessible attributes.
    for m in re.finditer(r"<img\b[^>]*>", src, re.I):
        tag = m.group(0)
        src_m = re.search(r'src="([^"]+)"', tag)
        if not src_m:
            errors.append(f"<img> without src: {tag[:60]}")
            continue
        target = (site / src_m.group(1)).resolve()
        if not target.is_file():
            errors.append(f"image not found: {src_m.group(1)}")
        for attr in IMG_ATTRS:
            if attr not in tag:
                errors.append(f"<img> missing {attr.rstrip('=')}: {src_m.group(1)}")

    # Internal links resolve.
    for m in re.finditer(r'href="([^"#][^"]*)"', src):
        href = m.group(1)
        if href.startswith(("http://", "https://", "mailto:", "tel:")):
            continue
        target = (site / href.split("#")[0]).resolve()
        if not target.exists():
            errors.append(f"broken internal link: {href}")

    # In-page anchors resolve, and ids are unique — a duplicated id silently
    # breaks aria-labelledby and every link that targets it.
    ids = re.findall(r'\sid="([^"]+)"', src)
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    for d in dupes:
        errors.append(f"duplicate id: {d}")
    idset = set(ids)
    for m in re.finditer(r'href="#([^"]+)"', src):
        if m.group(1) not in idset:
            errors.append(f"dead in-page anchor: #{m.group(1)}")

    # Every aria-labelledby / aria-describedby must point at a real id.
    for attr in ("aria-labelledby", "aria-describedby"):
        for m in re.finditer(rf'{attr}="([^"]+)"', src):
            for ref in m.group(1).split():
                if ref not in idset:
                    errors.append(f"{attr} points at missing id: {ref}")

    # Outbound links must not leak the referrer or the opener.
    for m in re.finditer(r'<a\b[^>]*href="https?://[^"]*"[^>]*>', src, re.I):
        tag = m.group(0)
        if 'rel="noopener"' not in tag:
            warnings.append(f"external link without rel=noopener: {tag[:70]}")

    # Heading levels must not skip (h1 straight to h3), or the outline is
    # unusable with a screen reader. Nothing in the stylesheet depends on the
    # tag, so the fix is always a swap.
    main_m = re.search(r"<main.*?</main>", src, re.S)
    body = main_m.group(0) if main_m else src
    prev = 0
    for m in re.finditer(r"<(h[1-4])\b[^>]*>(.*?)</\1>", body, re.S):
        lvl = int(m.group(1)[1])
        if prev and lvl > prev + 1:
            label = strip_tags(m.group(2)).strip()[:50]
            errors.append(f"heading level skips h{prev} -> h{lvl}: {label!r}")
        prev = lvl

    # A table needs a caption, and every header cell needs a scope.
    for tb in re.findall(r"<table\b.*?</table>", src, re.S):
        if "<caption" not in tb:
            errors.append("table without a <caption>")
        for th in re.findall(r"<th\b[^>]*>", tb):
            if "scope=" not in th:
                errors.append(f"<th> without scope: {th[:50]}")
                break

    # Alt text is a label, not a description — long ones are unusable aloud.
    for tag in re.findall(r"<img\b[^>]*>", src):
        alt_m = re.search(r'alt="([^"]*)"', tag)
        if alt_m and len(alt_m.group(1)) > 140:
            errors.append(f"alt text is {len(alt_m.group(1))} chars (limit 140)")

    # The social card is the most-seen asset on the site and nothing links to it
    # from a page body, so its absence would otherwise go unnoticed until a link
    # was shared. tools/make_og_card.py regenerates it.
    for m in re.finditer(r'<meta property="og:image" content="([^"]+)"', src):
        rel = m.group(1).lstrip("/")
        if not (site / rel).exists():
            errors.append(f"og:image does not exist: {rel}")

    # Link text has to make sense read out of context.
    for m in re.finditer(r"<a\b[^>]*>(.*?)</a>", src, re.S):
        text = strip_tags(m.group(1)).strip().lower()
        if text in {"here", "click here", "read more", "more", "link", "this"}:
            errors.append(f"link text means nothing out of context: {text!r}")

    return errors, warnings


def main() -> int:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "site").resolve()
    if not site.is_dir():
        sys.exit(f"Not a directory: {site}")

    pages = sorted(site.glob("*.html"))
    if not pages:
        sys.exit(f"No HTML pages in {site}")

    # Two pages sharing a <title> makes them indistinguishable in a tab, a
    # bookmark or a search result.
    seen: dict[str, str] = {}
    dup_titles: dict[str, list[str]] = {}
    for page in pages:
        m = re.search(r"<title>(.*?)</title>", page.read_text(encoding="utf-8"), re.S)
        if not m:
            continue
        title = html.unescape(m.group(1)).strip()
        if title in seen:
            dup_titles.setdefault(title, [seen[title]]).append(page.name)
        seen[title] = page.name

    total_errors = 0
    total_warnings = 0
    for page in pages:
        errors, warnings = check_page(page, site)
        for title, names in dup_titles.items():
            if page.name in names:
                errors.append(f"duplicate <title> shared by {', '.join(names)}: {title[:50]!r}")
        status = "OK  " if not errors else "FAIL"
        print(f"\n{status} {page.name}")
        for e in errors:
            print(f"       error   {e}")
        for w in warnings:
            print(f"       warn    {w}")
        total_errors += len(errors)
        total_warnings += len(warnings)

    print(f"\n{len(pages)} pages, {total_errors} errors, {total_warnings} warnings.")
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
