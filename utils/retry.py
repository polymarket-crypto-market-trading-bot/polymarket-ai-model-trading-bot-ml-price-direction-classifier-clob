"""Retry helpers for API calls."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

T = TypeVar("T")


def with_retry(
    func: Callable[..., T],
    *,
    attempts: int = 5,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
) -> Callable[..., T]:
    decorator = retry(
        reraise=True,
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=min_wait, max=max_wait),
        retry=retry_if_exception_type(
            (httpx.HTTPError, httpx.TimeoutException, ConnectionError, TimeoutError)
        ),
    )
    return decorator(func)
