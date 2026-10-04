#!/usr/bin/env python3
"""Stamp (or un-stamp) live demo links across the site.

The demos run behind Cloudflare *quick* tunnels, whose hostname changes on every
restart. Hardcoding one into a "visit the live site" button is therefore wrong —
but the day there is a stable address (a named tunnel, or Tailscale Funnel), every
project page should point at it.

This tool is that single switch. It rewrites the primary call-to-action inside each
page's entry block:

    live_urls.json has a URL  ->  "Open the live demo"  linking to it
    live_urls.json is empty   ->  "Ask for the live demo"  (a mailto request)

Edit tools/live_urls.json and re-run; nothing else in the page is touched. The
script is idempotent, so it is safe to run repeatedly.

It also sweeps *renamed* demo hostnames across every page, not just the project
pages. The home page and Project Work hand-author their own demo links in the
project cards, so a hostname change used to leave those two linking an address
that no longer resolves. List the old hostname under "_retired" in
live_urls.json and re-run; every occurrence anywhere in site/ is rewritten.

Usage:
    python3 tools/set_live_urls.py [--check] [site-dir]

    --check   report what would change without writing

Standard library only.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
from pathlib import Path

# page file -> (key in live_urls.json, mailto request, fallback label, live label)
PROJECTS: dict[str, tuple[str, str, str, str]] = {
    "openclaimflow.html": (
        "claims",
        "mailto:shreyashms2501@gmail.com?subject=OpenClaimFlow%20demo%20URL",
        "Ask for the live demo",
        "Open the live demo",
    ),
    "workflow.html": (
        "workflow",
        "mailto:shreyashms2501@gmail.com?subject=Workflow%20demo%20URL",
        "Ask for the live demo",
        "Open the live demo",
    ),
    "banking.html": (
        "banking",
        "mailto:shreyashms2501@gmail.com?subject=Banking%20demo%20URL",
        "Ask for the live demo",
        "Open the live demo",
    ),
    "cartographer.html": (
        "cartographer",
        "mailto:shreyashms2501@gmail.com?subject=Cartographer%20demo%20URL",
        "Ask for the live demo",
        "Open the live demo",
    ),
    "claimshield.html": (
        "claimshield",
        "mailto:shreyashms2501@gmail.com?subject=ClaimShield%20demo%20URL",
        "Ask for the live demo",
        "Open the live demo",
    ),
    "michiru.html": (
        "michiru",
        "mailto:shreyashms2501@gmail.com?subject=Michiru",
        "Ask about this project",
        "Open the live demo",
    ),
}

# The first primary button inside the entry block is the demo call to action.
CTA_RE = re.compile(
    r'(<div class="entry-actions">.*?)'
    r'<a class="btn btn-primary"([^>]*)>(.*?)</a>',
    re.S,
)


def rewrite(src: str, url: str, mailto: str, ask: str, label: str) -> tuple[str, bool]:
    def repl(m: re.Match[str]) -> str:
        pre, attrs, _text = m.group(1), m.group(2), m.group(3)
        attrs = re.sub(r'\s*href="[^"]*"', "", attrs)
        attrs = re.sub(r'\s*target="[^"]*"', "", attrs)
        attrs = re.sub(r'\s*rel="[^"]*"', "", attrs)
        attrs = " ".join(attrs.split())
        attrs = f" {attrs}" if attrs else ""
        if url:
            return f'{pre}<a class="btn btn-primary"{attrs} href="{url}" target="_blank" rel="noopener">{label}</a>'
        return f'{pre}<a class="btn btn-primary"{attrs} href="{mailto}">{ask}</a>'

    new, n = CTA_RE.subn(repl, src, count=1)
    return new, n == 1


def renames(urls: dict) -> dict[str, str]:
    """Map a retired demo URL to its current one, from "_retired" in the config.

    "_retired" holds the old hostname labels per project, e.g.
    {"claims": ["shreyash-claims"]}. The tailnet domain is taken from the live
    URLs so it is never hardcoded here.
    """
    live = {k: v.strip() for k, v in urls.items()
            if not k.startswith("_") and isinstance(v, str) and v.strip()}
    domain = ""
    for url in live.values():
        host = urllib.parse.urlsplit(url).hostname or ""
        if "." in host:
            domain = host.split(".", 1)[1]
            break
    if not domain:
        return {}

    out: dict[str, str] = {}
    retired = urls.get("_retired") or {}
    for key, labels in retired.items():
        current = live.get(key)
        if not current:
            continue
        for label in labels:
            out[f"https://{label}.{domain}"] = current
    return out


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check_only = "--check" in sys.argv

    root = Path(__file__).resolve().parent.parent
    site = Path(args[0]).resolve() if args else root / "site"
    config_path = Path(__file__).resolve().parent / "live_urls.json"

    if not site.is_dir():
        sys.exit(f"Not a directory: {site}")
    if not config_path.is_file():
        sys.exit(f"Missing {config_path}")

    urls: dict[str, str] = json.loads(config_path.read_text(encoding="utf-8"))

    changed = 0
    for page_name, (key, mailto, ask, label) in PROJECTS.items():
        page = site / page_name
        if not page.is_file():
            print(f"  skip   {page_name} (not written yet)")
            continue
        url = (urls.get(key) or "").strip()
        if url and not url.startswith(("http://", "https://")):
            sys.exit(f"  {key}: URL must start with http:// or https:// — got {url!r}")

        src = page.read_text(encoding="utf-8")
        new, ok = rewrite(src, url, mailto, ask, label)
        if not ok:
            print(f"  WARN   {page_name}: no entry-block CTA found; left untouched")
            continue
        if new == src:
            print(f"  same   {page_name} ({'live' if url else 'on request'})")
            continue
        changed += 1
        print(f"  {'would set' if check_only else 'set'}  {page_name} -> "
              f"{'live: ' + url if url else 'on request'}")
        if not check_only:
            page.write_text(new, encoding="utf-8")

    # Every other page — the home page and Project Work author their demo links
    # by hand inside the project cards, so a rename has to be swept through them.
    swept = 0
    for old, current in renames(urls).items():
        for page in sorted(site.glob("*.html")):
            src = page.read_text(encoding="utf-8")
            if old not in src:
                continue
            n = src.count(old)
            swept += n
            print(f"  {'would rewrite' if check_only else 'rewrote'}  "
                  f"{page.name}: {n}x {old} -> {current}")
            if not check_only:
                page.write_text(src.replace(old, current), encoding="utf-8")

    print(f"\n{changed} page(s) {'to change' if check_only else 'changed'}"
          + (f"; {swept} renamed link(s) swept." if swept else "."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
