"""
Retry Policy with Exponential Backoff

Provides configurable retry logic with exponential backoff and jitter
for transient failures.

Example:
    from src.resilience.retry import RetryPolicy

    retry_policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        jitter=True,
        name="object_detection"
    )

    result = retry_policy(detect_objects, frame)
"""

import time
import random
import logging
import asyncio
from typing import Callable, Any, TypeVar, Coroutine, Union
from functools import wraps
from dataclasses import dataclass

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class RetryMetrics:
    """Metrics for retry tracking."""
    total_attempts: int = 0
    total_failures: int = 0
    total_successes: int = 0
    retries_exhausted: int = 0
    total_wait_time: float = 0.0


class MaxRetriesExceeded(Exception):
    """Raised when all retry attempts are exhausted."""
    pass


class RetryPolicy:
    """
    Retry policy with exponential backoff and jitter.

    Implements smart retry logic for transient failures:
    - Exponential backoff: delay = base_delay * (2 ^ attempt)
    - Jitter: adds randomness to prevent thundering herd
    - Max delay: caps the exponential growth

    Attributes:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 300.0)
        jitter: Whether to add random jitter (default: True)
        backoff_multiplier: Exponential multiplier (default: 2.0)
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 300.0,
        jitter: bool = True,
        backoff_multiplier: float = 2.0,
        name: str = "RetryPolicy",
    ):
        """
        Initialize retry policy.

        Args:
            max_attempts: Maximum retry attempts (default: 3)
            base_delay: Initial delay in seconds (default: 1.0)
            max_delay: Maximum delay cap (default: 300.0)
            jitter: Add random jitter (default: True)
            backoff_multiplier: Exponential multiplier (default: 2.0)
            name: Policy identifier for logging (default: "RetryPolicy")
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.backoff_multiplier = backoff_multiplier
        self.name = name
        self.metrics = RetryMetrics()

    def __call__(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result from successful call

        Raises:
            MaxRetriesExceeded: If all attempts fail
        """
        last_exception = None

        for attempt in range(self.max_attempts):
            self.metrics.total_attempts += 1

            try:
                result = func(*args, **kwargs)
                self.metrics.total_successes += 1

                if attempt > 0:
                    logger.info(
                        f"[{self.name}] Succeeded on attempt {attempt + 1}/"
                        f"{self.max_attempts}"
                    )

                return result

            except Exception as e:
                last_exception = e
                self.metrics.total_failures += 1

                if attempt < self.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"[{self.name}] Attempt {attempt + 1}/"
                        f"{self.max_attempts} failed: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    self.metrics.total_wait_time += delay
                    time.sleep(delay)
                else:
                    logger.error(
                        f"[{self.name}] All {self.max_attempts} attempts failed"
                    )
                    self.metrics.retries_exhausted += 1

        raise MaxRetriesExceeded(
            f"Failed after {self.max_attempts} attempts: {last_exception}"
        )

    async def call_async(
        self,
        func: Union[
            Callable[..., Coroutine[Any, Any, T]],
            Callable[..., T]
        ],
        *args,
        **kwargs
    ) -> T:
        """
        Execute async function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result from successful call

        Raises:
            MaxRetriesExceeded: If all attempts fail
        """
        last_exception = None

        for attempt in range(self.max_attempts):
            self.metrics.total_attempts += 1

            try:
                # Handle both async and sync functions
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                self.metrics.total_successes += 1

                if attempt > 0:
                    logger.info(
                        f"[{self.name}] Succeeded on attempt {attempt + 1}/"
                        f"{self.max_attempts}"
                    )

                return result

            except Exception as e:
                last_exception = e
                self.metrics.total_failures += 1

                if attempt < self.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"[{self.name}] Attempt {attempt + 1}/"
                        f"{self.max_attempts} failed: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    self.metrics.total_wait_time += delay
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"[{self.name}] All {self.max_attempts} attempts failed"
                    )
                    self.metrics.retries_exhausted += 1

        raise MaxRetriesExceeded(
            f"Failed after {self.max_attempts} attempts: {last_exception}"
        )

    def decorator(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator for easy function wrapping.

        Args:
            func: Function to decorate

        Returns:
            Wrapped function with retry logic

        Example:
            @retry_policy.decorator
            def risky_function():
                pass
        """
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return self(func, *args, **kwargs)
        return wrapper

    async def async_decorator(
        self,
        func: Callable[..., Coroutine[Any, Any, T]]
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        """
        Decorator for async functions.

        Args:
            func: Async function to decorate

        Returns:
            Wrapped async function with retry logic
        """
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await self.call_async(func, *args, **kwargs)
        return wrapper

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number.

        Uses exponential backoff with optional jitter:
        delay = base_delay * (multiplier ^ attempt)
        jitter = random(0, delay) if enabled

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * (multiplier ^ attempt)
        delay = self.base_delay * (self.backoff_multiplier ** attempt)

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter
        if self.jitter:
            delay = random.uniform(0, delay)

        return delay

    def get_metrics(self) -> dict:
        """
        Get retry metrics.

        Returns:
            Dictionary with retry statistics
        """
        success_rate = (
            (self.metrics.total_successes / self.metrics.total_attempts * 100)
            if self.metrics.total_attempts > 0
            else 0
        )

        return {
            "name": self.name,
            "total_attempts": self.metrics.total_attempts,
            "total_successes": self.metrics.total_successes,
            "total_failures": self.metrics.total_failures,
            "retries_exhausted": self.metrics.retries_exhausted,
            "success_rate": f"{success_rate:.1f}%",
            "total_wait_time": f"{self.metrics.total_wait_time:.2f}s",
            "config": {
                "max_attempts": self.max_attempts,
                "base_delay": self.base_delay,
                "max_delay": self.max_delay,
                "jitter": self.jitter,
                "backoff_multiplier": self.backoff_multiplier,
            }
        }
