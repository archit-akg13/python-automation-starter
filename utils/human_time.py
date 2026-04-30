"""utils/human_time.py — human-readable duration & relative-time helpers.

Small, dependency-free formatting utilities used by CLI commands when logging
elapsed work, ETAs, or 'last run X ago' lines. Pure stdlib (datetime + math).

Examples:
    >>> humanize_duration(0.42)
    '420ms'
    >>> humanize_duration(75)
    '1m 15s'
    >>> humanize_duration(3725)
    '1h 2m 5s'
    >>> humanize_duration(90061)
    '1d 1h 1m'
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

_UNITS = (
    ("d", 86_400),
    ("h", 3_600),
    ("m", 60),
    ("s", 1),
)


def humanize_duration(seconds: float, max_parts: int = 3) -> str:
    """Format a duration in seconds as e.g. '1h 2m 5s'.

    Sub-second durations are returned in milliseconds (e.g. '420ms').
    Negative durations are formatted with a leading '-'.
    `max_parts` caps the number of unit segments included (default 3).
    """
    if math.isnan(seconds):
        return "nan"
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    if seconds < 1:
        return f"{sign}{int(round(seconds * 1000))}ms"

    parts: list[str] = []
    remaining = int(seconds)
    for label, size in _UNITS:
        if remaining >= size:
            value, remaining = divmod(remaining, size)
            parts.append(f"{value}{label}")
        if len(parts) == max_parts:
            break
    return sign + " ".join(parts) if parts else "0s"


def humanize_relative(when: datetime, now: datetime | None = None) -> str:
    """Return a phrase like 'in 5m' or '2h ago' relative to `now` (UTC default).

    Both inputs should be timezone-aware; naive datetimes are assumed UTC.
    """
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    delta = (when - now).total_seconds()
    if abs(delta) < 1:
        return "just now"
    formatted = humanize_duration(abs(delta), max_parts=2)
    return f"in {formatted}" if delta > 0 else f"{formatted} ago"


if __name__ == "__main__":
    # Quick smoke test when run directly: python -m utils.human_time
    samples = [0, 0.05, 0.42, 1, 59, 75, 3725, 90061, -42]
    for s in samples:
        print(f"{s:>8}s -> {humanize_duration(s)}")
