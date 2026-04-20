"""commands/healthcheck.py — `healthcheck` subcommand for the starter CLI.

Probes a list of HTTP endpoints (configured via env or CLI) and reports their
status, latency, and any TLS / connection errors. Designed as a reference
implementation for the "Adding a new subcommand" pattern in the project README:

    1. Define register(subparsers) — wires the subcommand into argparse.
    2. Define run(args)            — performs the work, returns an exit code.
    3. Import & call register(...) from main.py.

Usage:
    python -m main healthcheck                              # uses HEALTHCHECK_URLS from .env
    python -m main healthcheck --url https://example.com    # one-shot
    python -m main healthcheck --url https://a.com https://b.com --timeout 10 --json

Exit codes:
    0 — every endpoint returned a 2xx status
    1 — at least one endpoint failed (non-2xx, timeout, or connection error)
    2 — usage / setup error (no URLs supplied)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from typing import Iterable

from retry import retry

log = logging.getLogger(__name__)


@dataclass
class ProbeResult:
    url: str
    status: int | None
    latency_ms: float
    ok: bool
    error: str | None = None


def register(subparsers: argparse._SubParsersAction) -> None:
    """Wire the `healthcheck` subcommand into the CLI."""
    parser = subparsers.add_parser(
        "healthcheck",
        help="probe HTTP endpoints and report status + latency",
        description="Probe HTTP endpoints. URLs come from --url args or HEALTHCHECK_URLS (comma-separated).",
    )
    parser.add_argument(
        "--url",
        nargs="*",
        default=None,
        help="one or more URLs to probe (overrides HEALTHCHECK_URLS)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="per-request timeout in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="retry count per URL on transient failures (default: 2)",
    )
    parser.add_argument(
        "--user-agent",
        default="python-automation-starter/healthcheck",
        help="User-Agent header to send",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="emit JSON instead of a human-readable table",
    )
    parser.set_defaults(func=run)


def _resolve_urls(arg_urls: list[str] | None) -> list[str]:
    if arg_urls:
        return arg_urls
    raw = os.environ.get("HEALTHCHECK_URLS", "").strip()
    if not raw:
        return []
    return [u.strip() for u in raw.split(",") if u.strip()]


def _probe_once(url: str, timeout: float, user_agent: str) -> ProbeResult:
    """Single request — caller handles retry policy."""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed_ms = (time.monotonic() - start) * 1000
            status = resp.status
            return ProbeResult(
                url=url,
                status=status,
                latency_ms=round(elapsed_ms, 2),
                ok=200 <= status < 300,
            )
    except urllib.error.HTTPError as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        return ProbeResult(
            url=url,
            status=exc.code,
            latency_ms=round(elapsed_ms, 2),
            ok=False,
            error=f"HTTP {exc.code}: {exc.reason}",
        )
    except (urllib.error.URLError, ssl.SSLError, TimeoutError, OSError) as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        return ProbeResult(
            url=url,
            status=None,
            latency_ms=round(elapsed_ms, 2),
            ok=False,
            error=f"{type(exc).__name__}: {exc}",
        )


def probe(url: str, timeout: float, user_agent: str, retries: int) -> ProbeResult:
    """Probe one URL with retry-on-transient-failure policy."""
    @retry(attempts=retries + 1, base_delay=0.2, backoff=2.0, max_delay=2.0)
    def _attempt() -> ProbeResult:
        result = _probe_once(url, timeout, user_agent)
        # Retry only on connection-level errors — not on legitimate 4xx/5xx.
        if result.status is None:
            raise RuntimeError(result.error or "probe failed")
        return result

    try:
        return _attempt()
    except Exception as exc:
        return ProbeResult(url=url, status=None, latency_ms=0.0, ok=False, error=str(exc))


def _render_table(results: Iterable[ProbeResult]) -> str:
    rows = list(results)
    if not rows:
        return "(no endpoints probed)"
    width = max(len(r.url) for r in rows)
    header = f"{'URL':<{width}}  {'STATUS':>6}  {'LATENCY':>10}  RESULT"
    lines = [header, "-" * len(header)]
    for r in rows:
        status = str(r.status) if r.status is not None else "—"
        latency = f"{r.latency_ms:>8.2f}ms"
        result = "ok" if r.ok else (r.error or "fail")
        lines.append(f"{r.url:<{width}}  {status:>6}  {latency:>10}  {result}")
    return "
".join(lines)


def run(args: argparse.Namespace) -> int:
    urls = _resolve_urls(args.url)
    if not urls:
        log.error("no URLs supplied — pass --url or set HEALTHCHECK_URLS in .env")
        return 2

    log.info("probing %d endpoint(s) with timeout=%.1fs retries=%d",
             len(urls), args.timeout, args.retries)

    results = [
        probe(u, args.timeout, args.user_agent, args.retries)
        for u in urls
    ]

    if args.as_json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        print(_render_table(results))

    return 0 if all(r.ok for r in results) else 1
