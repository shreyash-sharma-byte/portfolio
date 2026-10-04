#!/usr/bin/env python3
"""Verify the live demo links the site publishes.

Reads tools/live_urls.json and checks every non-empty address twice, because
one check is not enough and the obvious one is worthless:

  1. Public DNS.  Ask a public resolver, over HTTPS, for the A records. This
     must come back non-empty AND must not be a 100.64.0.0/10 (Tailscale
     CGNAT) address. A missing record is NXDOMAIN, which is not a propagation
     delay -- the name does not exist in the zone.

  2. The real request.  Connect to the resolved *public* address while still
     sending the hostname in SNI and Host, and require HTTP 200 and a valid
     certificate for that hostname.

Why this exists: running `curl <demo-url>` on the host that serves the app
proves nothing. MagicDNS resolves the name to a 100.x tailnet address, so the
request goes straight to the local node and never touches the public Funnel.
It returns 200 in ~20ms even when the demo is completely unreachable from the
internet. That is the failure this script is built to catch.

Exit status is 0 only when every address passes both checks.

    python3 tools/check_demos.py
    python3 tools/check_demos.py --json
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import ssl
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
URLS = HERE / "live_urls.json"
SITE = HERE.parent / "site"
DOH = "https://dns.google/resolve"
TIMEOUT = 25


def published_addresses(host: str) -> tuple[str, list[str]]:
    """Ask a public resolver for the host's A records. Returns (status, addrs)."""
    req = urllib.request.Request(
        f"{DOH}?name={host}&type=A", headers={"accept": "application/dns-json"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        body = json.load(r)
    status = {0: "NOERROR", 2: "SERVFAIL", 3: "NXDOMAIN"}.get(
        body.get("Status"), str(body.get("Status"))
    )
    addrs = [a["data"] for a in body.get("Answer", []) if a.get("type") == 1]
    return status, addrs


def fetch_via(address: str, host: str) -> tuple[int, str]:
    """GET https://host/ through `address`, keeping SNI and Host correct.

    urllib and http.client both take a single host argument, so neither can
    express "connect here, but claim to be there". This does it by hand: the
    TCP connection and TLS SNI are aimed at the resolved public address while
    the certificate is verified against, and the request names, the hostname.
    """
    ctx = ssl.create_default_context()
    raw = socket.create_connection((address, 443), timeout=TIMEOUT)
    try:
        with ctx.wrap_socket(raw, server_hostname=host) as tls:
            tls.sendall(
                f"GET / HTTP/1.1\r\nHost: {host}\r\n"
                "User-Agent: check_demos.py\r\nAccept: */*\r\n"
                "Connection: close\r\n\r\n".encode()
            )
            chunks = []
            while True:
                block = tls.recv(65536)
                if not block:
                    break
                chunks.append(block)
                if sum(len(c) for c in chunks) > 200_000:
                    break
    finally:
        try:
            raw.close()
        except OSError:
            pass
    head = b"".join(chunks).split(b"\r\n", 1)[0].decode("latin-1", "replace")
    parts = head.split()
    code = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return code, head


def cgnat(addr: str) -> bool:
    """True for Tailscale's 100.64.0.0/10 range: a private address, not a Funnel."""
    try:
        return ipaddress.ip_address(addr) in ipaddress.ip_network("100.64.0.0/10")
    except ValueError:
        return False


def stale_links(demos: dict[str, str]) -> list[str]:
    """Demo URLs written into the site's HTML that no longer match the config.

    The project pages are stamped by set_live_urls.py, but the home page and
    Project Work author their demo links by hand — which is how two renamed
    hostnames sat on those pages pointing at addresses that did not resolve.
    """
    current = {u.rstrip("/") for u in demos.values()}
    domain = ""
    for url in current:
        host = urllib.parse.urlsplit(url).hostname or ""
        if "." in host:
            domain = host.split(".", 1)[1]
            break
    if not domain or not SITE.is_dir():
        return []

    seen: dict[str, set[str]] = {}
    for page in sorted(SITE.glob("*.html")):
        for m in re.finditer(r"https://[a-z0-9-]+\." + re.escape(domain),
                             page.read_text(encoding="utf-8")):
            seen.setdefault(m.group(0), set()).add(page.name)

    problems = [f"stale demo URL on {', '.join(sorted(pages))}: {url}"
                for url, pages in sorted(seen.items()) if url not in current]
    problems += [f"published in live_urls.json but linked from no page: {url}"
                 for url in sorted(current) if url not in seen]
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", default=str(URLS))
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    data = json.loads(Path(args.urls).read_text(encoding="utf-8"))
    demos = {k: v for k, v in data.items()
             if not k.startswith("_") and isinstance(v, str) and v.strip()}

    results, failures = [], 0
    for name, url in sorted(demos.items()):
        host = urllib.parse.urlsplit(url).hostname or ""
        row = {"name": name, "url": url, "host": host}

        try:
            status, addrs = published_addresses(host)
        except Exception as exc:  # network or resolver failure
            status, addrs = f"ERROR {exc}", []

        if not addrs:
            row["dns"] = f"{status} — no public A record"
            row["ok"] = False
            if not args.json:
                print(f"FAIL  {name:14s} {row['dns']}")
            results.append(row)
            failures += 1
            continue
        if any(cgnat(a) for a in addrs):
            row["dns"] = f"{status} but CGNAT: {addrs}"
            row["ok"] = False
            if not args.json:
                print(f"FAIL  {name:14s} {row['dns']} — that is a tailnet address, not the Funnel")
            results.append(row)
            failures += 1
            continue
        row["dns"] = f"{status} {addrs}"

        code, detail = 0, ""
        last = None
        for addr in addrs:
            try:
                code, detail = fetch_via(addr, host)
                if code == 200:
                    last = None
                    break
            except Exception as exc:
                code, detail = 0, str(exc)
            last = detail
        row["http"] = code
        row["ok"] = code == 200
        if not row["ok"]:
            failures += 1
            if not args.json:
                print(f"FAIL  {name:14s} public DNS ok, but the request failed: "
                      f"{code or last}  {host}")
        elif not args.json:
            print(f"OK    {name:14s} {addrs[0]:16s} HTTP {code}  {host}")
        results.append(row)

    problems = stale_links(demos)
    if args.json:
        print(json.dumps({"demos": results, "link_problems": problems}, indent=2))
    else:
        for p in problems:
            print(f"FAIL  {p}")
        failures += len(problems)
        print(f"\n{len(demos)} demos, {failures} failing.")
        if failures:
            print("A FAIL above means a link on the site is dead for anyone "
                  "outside this machine.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
