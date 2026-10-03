#!/usr/bin/env python3
"""Stamp the site's public address into every page — or remove it again.

Until this runs, no page knows its own URL. That breaks the two things that
decide whether a shared link advertises anything at all:

  * `og:image` is a *relative* path. Every social platform resolves it against
    nothing, so a link posted to LinkedIn, WhatsApp or Slack renders as a bare
    line of text with no card.
  * With no `rel="canonical"`, a search engine has to guess which URL is the
    real one, and the site's own description may be replaced with a snippet it
    scrapes instead.

Point this at the site's base URL and all four tags become absolute on all ten
pages:

    og:image, twitter:image   ->  <base>/assets/og-card.png
    og:url, rel=canonical     ->  <base>/<page>

It also writes `sitemap.xml` and `robots.txt`, because those need the same single
fact and there is no reason for a second place to know the domain.

The script is idempotent: re-running with a new base rewrites the old one, and
`--clear` returns every page to the relative, host-unknown form.

Usage:
    python3 tools/set_site_url.py https://example.com [site-dir]
    python3 tools/set_site_url.py --clear [site-dir]
    python3 tools/set_site_url.py --check [site-dir]

Standard library only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

OG_IMAGE = "assets/og-card.png"
PAGES = (
    "index.html", "work.html", "about.html", "notes.html",
    "openclaimflow.html", "banking.html", "workflow.html",
    "michiru.html", "cartographer.html", "claimshield.html",
)

# An absolute or relative value already sitting in any of the tags we manage.
ANY_URL = r'[^"]*'


def page_url(base: str, page: str) -> str:
    if page == "index.html":
        return f"{base}/"
    return f"{base}/{page}"


def stamp(src: str, base: str | None, page: str) -> tuple[str, int]:
    """Return (new_source, number_of_tags_written)."""
    changes = 0

    # og:* tags use property=, twitter:* tags use name=. Both must become
    # absolute or the shared card has an image and the tweet's does not.
    image = f"{base}/{OG_IMAGE}" if base else OG_IMAGE
    for attr, prop in (("property", "og:image"), ("name", "twitter:image")):
        pat = rf'(<meta {attr}="{prop}" content="){ANY_URL}(")'
        src, n = re.subn(pat, lambda m: m.group(1) + image + m.group(2), src, count=1)
        changes += n

    # og:url and canonical are added when a base exists, and removed when it does
    # not — so a cleared site carries no stale absolute URL anywhere.
    for pat, template in (
        (rf'\n?<meta property="og:url" content="{ANY_URL}">', '<meta property="og:url" content="{v}">'),
        (rf'\n?<link rel="canonical" href="{ANY_URL}">', '<link rel="canonical" href="{v}">'),
    ):
        src = re.sub(pat, "", src)
        if base:
            value = page_url(base, page)
            anchor = '<meta name="twitter:card"'
            src = src.replace(anchor, template.format(v=value) + "\n" + anchor, 1)
            changes += 1

    return src, changes


def write_crawler_files(site: Path, base: str | None) -> None:
    """sitemap.xml and robots.txt, or remove them when the address is cleared."""
    sitemap, robots = site / "sitemap.xml", site / "robots.txt"
    if base is None:
        for f in (sitemap, robots):
            f.unlink(missing_ok=True)
        return

    urls = "".join(
        f"  <url><loc>{page_url(base, p)}</loc></url>\n" for p in PAGES
    )
    sitemap.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}</urlset>\n",
        encoding="utf-8",
    )
    robots.write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n",
        encoding="utf-8",
    )


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    flags = {a for a in sys.argv[1:] if a.startswith("-")}
    check = "--check" in flags
    clear = "--clear" in flags

    if clear:
        base = None
    elif args:
        base = args[0].rstrip("/")
        if not base.startswith(("http://", "https://")):
            sys.exit(f"Base URL must start with http:// or https:// — got {base!r}")
    else:
        sys.exit(__doc__)

    site = Path(args[1] if len(args) > 1 else "site").resolve()
    if not site.is_dir():
        sys.exit(f"Not a directory: {site}")

    written = 0
    for page in PAGES:
        path = site / page
        if not path.exists():
            sys.exit(f"Missing page: {path}")
        src = original = path.read_text(encoding="utf-8")
        src, n = stamp(src, base, page)
        if src != original:
            written += 1
            if not check:
                path.write_text(src, encoding="utf-8")
        print(f"  {page:22} {n} tags  {'(would change)' if check and src != original else ''}")

    verb = "would update" if check else "updated"
    what = "cleared" if clear else f"set to {base}"
    if not check:
        write_crawler_files(site, base)
    print(f"\n{written}/{len(PAGES)} pages {verb} — address {what}.")
    print("sitemap.xml and robots.txt " + ("removed." if clear else ("would be written."
          if check else "written.")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
