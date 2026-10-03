#!/usr/bin/env python3
"""Render the social card — the image every shared link shows.

This is the single most-seen asset on the site: it is what appears in a LinkedIn
post, a WhatsApp message, a Slack unfurl. It is also the easiest thing on the site
to forget, because nothing links to it, no checker reads it, and it is a binary.

It had already drifted. The shipped card claimed "800+ automated tests written"
months after that figure was corrected to 521, said "systems built & deployed" when
only five of six are hosted, and carried an earlier positioning line. None of that
is visible from the site, and all of it is visible to everyone the link reaches.

So the card is generated from the same facts as the pages, and regenerating it is
one command:

    python3 tools/make_og_card.py

Chrome does the rendering, so no image library is needed and the card uses the same
system font stacks as the site. Re-run it whenever a headline figure changes.

Standard library only.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

W, H = 1200, 630

# Keep these in step with the proof strip on site/index.html. They are the only
# figures the card states, and each one is verifiable on a project page.
EYEBROW = "Full-stack engineer \u00b7 Pune, India"
NAME = "Shreyash Sharma"
LEDE = (
    "Three years in insurance and banking. Six systems built end to end in Java, Spring "
    "Boot and Angular \u2014 every figure on the site traces to a file, a commit or a run."
)
STATS = (
    ("3 yrs", "insurance &amp; banking"),
    ("20+", "projects delivered"),
    ("70,000", "policies a day"),
    ("5", "live demos to try"),
)
FOOT_LEFT = "github.com/shreyash-sharma-byte"
# The right-hand slot used to read "Every page states what is unfinished" — the
# same defect-forward framing removed from the site. A shared card should carry a
# way to make contact instead.
FOOT_RIGHT = "shreyashms2501@gmail.com"

SANS = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace'

CARD = f"""<!doctype html>
<meta charset="utf-8">
<style>
  html, body {{ margin: 0; padding: 0; width: {W}px; height: {H}px; }}
  body {{
    box-sizing: border-box; padding: 58px 72px 46px;
    background: #ffffff; color: #14161a;
    font-family: {SANS};
    display: flex; flex-direction: column;
    border-top: 6px solid #0b5c62;
  }}
  .eyebrow {{
    font-family: {MONO}; font-size: 15px; letter-spacing: 0.14em;
    text-transform: uppercase; color: #6a7280;
  }}
  h1 {{ font-size: 74px; font-weight: 700; letter-spacing: -0.025em; margin: 8px 0 0; }}
  .lede {{
    font-size: 26px; line-height: 1.42; color: #3c424c;
    margin: 20px 0 0; max-width: 1000px;
  }}
  .stats {{
    display: flex; margin-top: auto;
    border-top: 1px solid #e5e6e9; border-bottom: 1px solid #e5e6e9;
    padding: 24px 0;
  }}
  .stat {{ flex: 1; }}
  .stat b {{
    display: block; font-family: {MONO}; font-size: 38px; font-weight: 600;
    letter-spacing: -0.01em;
  }}
  .stat span {{ display: block; font-size: 16px; color: #6a7280; margin-top: 5px; }}
  .foot {{
    display: flex; justify-content: space-between; margin-top: 22px;
    font-family: {MONO}; font-size: 16px; color: #6a7280;
  }}
</style>
<div class="eyebrow">{EYEBROW}</div>
<h1>{NAME}</h1>
<p class="lede">{LEDE}</p>
<div class="stats">
{"".join(f'  <div class="stat"><b>{n}</b><span>{label}</span></div>' + chr(10) for n, label in STATS)}</div>
<div class="foot"><span>{FOOT_LEFT}</span><span>{FOOT_RIGHT}</span></div>
"""

# Phrases this card must never carry again: retired figures, over-claims, and the
# "a mistake is expensive" pitch that read as marketing rather than as a person.
BANNED = ("800+", "deployed projects", "built &amp; deployed", "mistake is expensive")


def main() -> int:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "site").resolve()
    out = site / "assets" / "og-card.png"
    if not out.parent.is_dir():
        sys.exit(f"No such directory: {out.parent}")

    # The card must not repeat a claim the site has retired. This is the failure
    # that prompted the generator, so it is checked rather than trusted.
    for phrase in BANNED:
        if phrase in CARD:
            sys.exit(f"Refusing to render: the card still says {phrase!r}")

    chrome = next(
        (p for name in ("google-chrome", "chromium", "chromium-browser")
         if (p := shutil.which(name))),
        None,
    )
    if not chrome:
        sys.exit("No Chrome/Chromium found; cannot render the card.")

    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "card.html"
        html.write_text(CARD, encoding="utf-8")
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
             "--hide-scrollbars", f"--window-size={W},{H}",
             f"--screenshot={out}", "--virtual-time-budget=6000", html.as_uri()],
            capture_output=True, check=True,
        )

    size = out.stat().st_size
    print(f"wrote {out} ({W}x{H}, {size // 1024} KB)")
    print("  " + " | ".join(f"{n} {re.sub('&amp;', '&', l)}" for n, l in STATS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
