#!/usr/bin/env python3
"""Layout verifier for the portfolio site.

Renders every page in headless Chrome at phone (390px) and desktop (1280px) width
and reports, per page:

  * documentElement.scrollWidth  — must equal the viewport width
  * every element whose box extends past the viewport, with its class
  * every `.pre` ASCII diagram that scrolls inside its own box, with its
    column count (the stylesheet promises all of them fit 48 columns)

This exists because the standing rule is "no horizontal scrolling at 390px or
1280px", and because a page can look correct while a single child silently sizes
a column wider than the screen. Measuring geometry beats eyeballing it.

Usage:
    python3 tools/verify_layout.py [site-dir]
Exit status is 1 if any page overflows.

Standard library only. Chrome is used as the renderer; nothing is installed.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WIDTHS = (390, 1280)
HEIGHT = 900

CHROME_CANDIDATES = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
)

HARNESS = """<!doctype html>
<meta charset="utf-8">
<title>harness</title>
<body>
<pre id="out">PENDING</pre>
<script>
const PAGES = %(pages)s;
const WIDTHS = %(widths)s;
const HEIGHT = %(height)d;
const results = [];

function measure(url, width) {
  return new Promise((resolve) => {
    const f = document.createElement('iframe');
    f.style.cssText = 'width:' + width + 'px;height:' + HEIGHT +
                      'px;border:0;position:absolute;left:-99999px;top:0';
    f.src = url;
    const done = () => {
      const r = { url: url.split('/').pop(), width: width };
      try {
        const d = f.contentDocument;
        const de = d.documentElement;
        r.scrollWidth = de.scrollWidth;
        r.clientWidth = de.clientWidth;
        // Only right-edge overflow creates horizontal scrolling in LTR. An
        // element parked entirely off to the left (the visually-hidden skip
        // link) is clipped and cannot scroll the page, so it is not a defect.
        // Content inside an explicit scroll container is also contained by
        // design — a wide table in an overflow-x:auto wrapper must not be
        // reported as a page-level overflow, or the tool punishes the fix.
        const scrollable = (el) => {
          let p = el.parentElement;
          while (p && p !== d.documentElement) {
            const ox = d.defaultView.getComputedStyle(p).overflowX;
            if (ox === 'auto' || ox === 'scroll' || ox === 'hidden') return true;
            p = p.parentElement;
          }
          return false;
        };
        const bad = [];
        const clipped = [];
        const contained = [];
        for (const el of d.querySelectorAll('*')) {
          const rect = el.getBoundingClientRect();
          if (rect.width <= 0) continue;
          const cls = (typeof el.className === 'string' ? el.className : '');
          const info = {
            tag: el.tagName.toLowerCase(),
            cls: cls.slice(0, 70),
            left: Math.round(rect.left),
            right: Math.round(rect.right),
            width: Math.round(rect.width)
          };
          if (rect.right > width + 1) {
            if (scrollable(el)) { contained.push(info); } else { bad.push(info); }
          } else if (rect.left < -1 && rect.right > 0) {
            clipped.push(info);
          }
        }
        r.overflowCount = bad.length;
        r.overflow = bad.slice(0, 10);
        r.containedCount = contained.length;
        r.clippedCount = clipped.length;
        r.clipped = clipped.slice(0, 5);
        // The stylesheet promises every ASCII diagram is authored to <=48
        // columns so it never scrolls inside its own box at 390px. Assert
        // that instead of trusting the comment.
        r.preScrolling = [];
        r.maxDiagramCols = 0;
        for (const el of d.querySelectorAll('.pre')) {
          let cols = 0;
          for (const line of el.textContent.split(String.fromCharCode(10))) {
            cols = Math.max(cols, line.length);
          }
          r.maxDiagramCols = Math.max(r.maxDiagramCols, cols);
          if (el.scrollWidth > el.clientWidth + 1) {
            r.preScrolling.push({ cols: cols, scroll: el.scrollWidth,
                                  client: el.clientWidth });
          }
        }
      } catch (e) {
        r.error = String(e);
      }
      results.push(r);
      resolve();
    };
    f.onload = () => setTimeout(done, 300);
    document.body.appendChild(f);
  });
}

(async () => {
  for (const p of PAGES) {
    for (const w of WIDTHS) {
      await measure(p, w);
    }
  }
  document.getElementById('out').textContent = 'RESULTS_JSON:' + JSON.stringify(results);
})();
</script>
"""


def find_chrome() -> str:
    for name in CHROME_CANDIDATES:
        path = shutil.which(name)
        if path:
            return path
    sys.exit("No Chrome/Chromium binary found; cannot verify layout.")


def run_harness(chrome: str, pages: list[str]) -> list[dict]:
    harness = HARNESS % {
        "pages": json.dumps(pages),
        "widths": json.dumps(list(WIDTHS)),
        "height": HEIGHT,
    }
    with tempfile.TemporaryDirectory() as tmp:
        harness_path = Path(tmp) / "harness.html"
        harness_path.write_text(harness, encoding="utf-8")
        cmd = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--allow-file-access-from-files",
            "--hide-scrollbars",
            "--virtual-time-budget=30000",
            "--dump-dom",
            harness_path.as_uri(),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        out = proc.stdout

    match = re.search(r"RESULTS_JSON:(\[.*?\])</pre>", out, re.S)
    if not match:
        sys.stderr.write(proc.stderr[-2000:] + "\n")
        sys.exit("Harness produced no results — Chrome may have failed to start.")
    return json.loads(html.unescape(match.group(1)))


def main() -> int:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "site").resolve()
    if not site.is_dir():
        sys.exit(f"Not a directory: {site}")

    pages = sorted(p.as_uri() for p in site.glob("*.html"))
    if not pages:
        sys.exit(f"No HTML pages in {site}")

    chrome = find_chrome()
    results = run_harness(chrome, pages)

    failures = 0
    by_page: dict[str, list[dict]] = {}
    for r in results:
        by_page.setdefault(r["url"], []).append(r)

    for page in sorted(by_page):
        print(f"\n{page}")
        for r in sorted(by_page[page], key=lambda x: x["width"]):
            if "error" in r:
                print(f"  {r['width']:>5}px  ERROR: {r['error']}")
                failures += 1
                continue
            over = r["overflowCount"]
            flag = "OK  " if over == 0 else "FAIL"
            cols = f"  diagrams<={r['maxDiagramCols']}cols" if r.get("maxDiagramCols") else ""
            print(f"  {r['width']:>5}px  {flag} scrollWidth={r['scrollWidth']:<6} "
                  f"viewport={r['width']:<6} overflowing={over}{cols}")
            if over:
                failures += 1
                for el in r["overflow"]:
                    cls = f".{el['cls']}" if el["cls"] else ""
                    print(f"          <{el['tag']}{cls}> width={el['width']} "
                          f"right={el['right']}")
            for dg in r.get("preScrolling", []):
                failures += 1
                print(f"          .pre scrolls: {dg['cols']} columns, "
                      f"{dg['scroll']}px inside {dg['client']}px")

    print(f"\n{len(results)} measurements, {failures} failing.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
