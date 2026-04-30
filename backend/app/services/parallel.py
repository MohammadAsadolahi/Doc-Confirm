"""
Parallel LLM execution utilities with semaphore-based rate limiting.
Prevents overwhelming the LLM endpoint with too many concurrent requests.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine, TypeVar

T = TypeVar("T")

# Global semaphore — limits concurrent LLM calls
_MAX_CONCURRENT_LLM_CALLS = 5
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(_MAX_CONCURRENT_LLM_CALLS)
    return _semaphore


async def throttled_call(coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine with semaphore throttling."""
    sem = _get_semaphore()
    async with sem:
        return await coro


async def parallel_map(
    func: Callable[..., Coroutine[Any, Any, T]],
    items: list,
    *args: Any,
    **kwargs: Any,
) -> list[T]:
    """
    Apply an async function to each item in parallel, with semaphore throttling.
    func(item, *args, **kwargs) for each item.
    Returns results in the same order as items.
    """
    tasks = [throttled_call(func(item, *args, **kwargs)) for item in items]
    return await asyncio.gather(*tasks, return_exceptions=True)


async def parallel_calls(*coros: Coroutine[Any, Any, Any]) -> list[Any]:
    """
    Run multiple coroutines in parallel with semaphore throttling.
    Returns results in the same order.
    """
    tasks = [throttled_call(c) for c in coros]
    return await asyncio.gather(*tasks, return_exceptions=True)
