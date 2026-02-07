"""
Circuit Breaker Pattern Implementation

Provides automatic failure handling with three states:
- CLOSED: Normal operation, failures are tracked
- OPEN: Failing repeatedly, requests are blocked
- HALF_OPEN: Testing recovery after timeout

Example:
    from src.resilience.circuit_breaker import CircuitBreaker

    ptz_breaker = CircuitBreaker(
        failure_threshold=5,
        timeout=30.0,
        name="ptz_control"
    )

    @ptz_breaker
    def pan_camera(angle):
        # ... PTZ command implementation
        pass

    try:
        pan_camera(45)
    except CircuitBreakerOpen:
        logger.error("PTZ circuit breaker is open, retrying later")
"""

import time
import logging
from enum import Enum
from typing import Callable, TypeVar
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"           # Normal operation
    OPEN = "open"               # Blocking requests
    HALF_OPEN = "half_open"     # Testing recovery


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreakerTimeout(Exception):
    """Raised when HALF_OPEN timeout is exceeded."""
    pass


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker monitoring."""
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    total_calls: int = 0
    total_successes: int = 0
    total_failures: int = 0
    last_failure_time: float = field(default_factory=time.time)
    opened_at: float = field(default_factory=time.time)
    last_state_change: float = field(default_factory=time.time)
    total_rejections: int = 0


class CircuitBreaker:
    """
    Circuit breaker for handling transient failures.

    Implements the circuit breaker pattern to prevent cascading failures
    by stopping requests when a service is experiencing issues.

    Attributes:
        name: Identifier for logging
        failure_threshold: Number of failures before opening circuit
        timeout: Seconds to wait before attempting recovery (HALF_OPEN)
        success_threshold: Successes in HALF_OPEN before closing
        expected_exception: Exception type that triggers the breaker
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 30.0,
        success_threshold: int = 2,
        expected_exception: type = Exception,
        name: str = "CircuitBreaker"
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening (default: 5)
            timeout: Seconds before attempting recovery (default: 30.0)
            success_threshold: Successes in HALF_OPEN to close (default: 2)
            expected_exception: Exception type to catch (default: Exception)
            name: Identifier for logging (default: "CircuitBreaker")
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        self.expected_exception = expected_exception

        self.metrics = CircuitBreakerMetrics()
        self._lock = False

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self.metrics.state

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            CircuitBreakerOpen: If circuit is OPEN
            CircuitBreakerTimeout: If HALF_OPEN timeout exceeded
        """
        self.metrics.total_calls += 1

        if self.metrics.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
                logger.info(f"[{self.name}] Attempting recovery (HALF_OPEN)")
            else:
                self.metrics.total_rejections += 1
                elapsed = time.time() - self.metrics.opened_at
                raise CircuitBreakerOpen(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Opened {elapsed:.1f}s ago. "
                    f"Will retry in {self.timeout - elapsed:.1f}s"
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure(e)
            raise

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator usage: @circuit_breaker

        Args:
            func: Function to decorate

        Returns:
            Wrapped function with circuit breaker protection
        """
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return self.call(func, *args, **kwargs)
        return wrapper

    def _on_success(self) -> None:
        """Handle successful execution."""
        self.metrics.success_count += 1
        self.metrics.total_successes += 1

        if self.metrics.state == CircuitBreakerState.HALF_OPEN:
            if self.metrics.success_count >= self.success_threshold:
                self._transition_to_closed()
                logger.info(
                    f"[{self.name}] Circuit closed after "
                    f"{self.metrics.success_count} successes"
                )
        else:
            # Reset failure count on success
            self.metrics.failure_count = 0

    def _on_failure(self, exc: Exception) -> None:
        """Handle failed execution."""
        self.metrics.failure_count += 1
        self.metrics.total_failures += 1
        self.metrics.last_failure_time = time.time()

        logger.warning(
            f"[{self.name}] Failure {self.metrics.failure_count}/"
            f"{self.failure_threshold}: {exc}"
        )

        if self.metrics.state == CircuitBreakerState.HALF_OPEN:
            self._transition_to_open()
            logger.error(
                f"[{self.name}] Recovery failed, circuit reopened"
            )
        elif self.metrics.failure_count >= self.failure_threshold:
            self._transition_to_open()
            logger.error(
                f"[{self.name}] Failure threshold reached, "
                f"circuit opened ({self.failure_threshold} failures)"
            )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        elapsed = time.time() - self.metrics.opened_at
        return elapsed >= self.timeout

    def _transition_to_open(self) -> None:
        """Transition circuit to OPEN state."""
        self.metrics.state = CircuitBreakerState.OPEN
        self.metrics.opened_at = time.time()
        self.metrics.last_state_change = time.time()
        self.metrics.success_count = 0

    def _transition_to_half_open(self) -> None:
        """Transition circuit to HALF_OPEN state."""
        self.metrics.state = CircuitBreakerState.HALF_OPEN
        self.metrics.last_state_change = time.time()
        self.metrics.success_count = 0
        self.metrics.failure_count = 0

    def _transition_to_closed(self) -> None:
        """Transition circuit to CLOSED state."""
        self.metrics.state = CircuitBreakerState.CLOSED
        self.metrics.last_state_change = time.time()
        self.metrics.failure_count = 0
        self.metrics.success_count = 0

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED."""
        self._transition_to_closed()
        logger.info(f"[{self.name}] Circuit manually reset to CLOSED")

    def get_status(self) -> dict:
        """
        Get detailed status of circuit breaker.

        Returns:
            Dictionary with state and metrics
        """
        elapsed_since_open = (
            time.time() - self.metrics.opened_at
            if self.metrics.state == CircuitBreakerState.OPEN
            else 0
        )

        return {
            "name": self.name,
            "state": self.metrics.state.value,
            "failure_count": self.metrics.failure_count,
            "success_count": self.metrics.success_count,
            "total_calls": self.metrics.total_calls,
            "total_rejections": self.metrics.total_rejections,
            "failure_threshold": self.failure_threshold,
            "success_threshold": self.success_threshold,
            "timeout": self.timeout,
            "elapsed_since_open": elapsed_since_open,
            "last_state_change": datetime.fromtimestamp(
                self.metrics.last_state_change
            ).isoformat(),
        }
