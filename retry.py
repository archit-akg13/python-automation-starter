"""Retry utilities with exponential backoff and jitter.

Drop-in decorator for wrapping flaky network calls, database queries,
or any transient-failure-prone operation.

Usage:
    from retry import retry

    @retry(max_attempts=5, initial_delay=0.5, max_delay=30.0)
    def fetch_data(url: str) -> dict:
        ...

The decorator uses full jitter (random delay between 0 and the computed
backoff) which is well-suited for avoiding thundering-herd retries.
"""

from __future__ import annotations

import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Tuple, Type, TypeVar

LOG = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
) -> Callable[[F], F]:
    """Retry a callable with exponential backoff.

    Args:
        max_attempts: Total attempts, including the first. Must be >= 1.
        initial_delay: Seconds to wait before the second attempt.
        max_delay: Hard cap on the backoff delay in seconds.
        backoff_factor: Multiplier applied after each failure.
        jitter: If True, use full jitter (random in [0, delay]).
        exceptions: Tuple of exception types that trigger a retry.

    Returns:
        A decorator that wraps the target function.

    Raises:
        ValueError: If max_attempts < 1 or delays are non-positive.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if initial_delay <= 0 or max_delay <= 0:
        raise ValueError("delays must be positive")

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            last_exc: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        LOG.warning(
                            "retry: %s failed after %d attempts",
                            func.__name__,
                            attempt,
                        )
                        raise
                    sleep_for = random.uniform(0, delay) if jitter else delay
                    LOG.info(
                        "retry: %s attempt %d/%d failed (%s); sleeping %.2fs",
                        func.__name__,
                        attempt,
                        max_attempts,
                        exc,
                        sleep_for,
                    )
                    time.sleep(sleep_for)
                    delay = min(delay * backoff_factor, max_delay)
            # Defensive - loop always returns or raises, but mypy wants this.
            assert last_exc is not None
            raise last_exc

        return wrapper  # type: ignore[return-value]

    return decorator


__all__ = ["retry"]
