"""
Shared Gemini API Call Utility with Exponential Backoff Retry
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Wraps all Gemini API calls across the codebase with a consistent retry pattern:
- 3 attempts maximum
- Exponential backoff: 1s, 2s, 4s delays
- Returns None on exhausted retries (callers fall back to deterministic logic)
"""

import asyncio
import logging
from typing import Any

logger = logging.getLogger("medikiosk.gemini_retry")

DEFAULT_MAX_RETRIES = 3
DEFAULT_DELAYS = [1, 2, 4]
DEFAULT_TIMEOUT_SECONDS = 15.0


def gemini_call_with_retry(
    client: Any,
    model: str,
    contents: Any,
    max_retries: int = DEFAULT_MAX_RETRIES,
    delays: list[int] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Any:
    """
    Synchronous Gemini call with exponential backoff retry.
    """
    if delays is None:
        delays = DEFAULT_DELAYS

    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
            )
            return response
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = delays[min(attempt, len(delays) - 1)]
                logger.warning(
                    f"Gemini call attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                import time
                time.sleep(delay)
            else:
                logger.error(
                    f"Gemini call exhausted all {max_retries} retries. Last error: {e}"
                )

    return None


async def gemini_call_with_retry_async(
    client: Any,
    model: str,
    contents: Any,
    max_retries: int = DEFAULT_MAX_RETRIES,
    delays: list[int] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Any:
    """
    Async wrapper for Gemini call with exponential backoff retry.
    Uses asyncio.to_thread to avoid blocking the event loop and asyncio.wait_for for bounded execution.
    """
    if delays is None:
        delays = DEFAULT_DELAYS

    last_error = None
    for attempt in range(max_retries):
        try:
            # Run the synchronous SDK call in a worker thread with bounded timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=model,
                    contents=contents,
                ),
                timeout=timeout,
            )
            return response
        except asyncio.TimeoutError:
            last_error = TimeoutError(f"Gemini call timed out after {timeout}s")
            logger.warning(f"Gemini call attempt {attempt + 1}/{max_retries} timed out after {timeout}s.")
        except Exception as e:
            last_error = e
            logger.warning(f"Gemini async call attempt {attempt + 1}/{max_retries} failed: {e}.")

        if attempt < max_retries - 1:
            delay = delays[min(attempt, len(delays) - 1)]
            logger.warning(f"Retrying Gemini call in {delay}s...")
            await asyncio.sleep(delay)
        else:
            logger.error(
                f"Gemini async call exhausted all {max_retries} retries. Last error: {last_error}"
            )

    return None

