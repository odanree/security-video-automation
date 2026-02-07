"""
Resilience Layer

Production-grade resilience patterns for handling failures gracefully:
- Circuit Breaker: Prevent cascading failures
- Retry Policy: Recover from transient failures
- Health Monitor: System health tracking and alerts

Example:
    from src.resilience import CircuitBreaker, RetryPolicy, HealthMonitor

    ptz_breaker = CircuitBreaker(failure_threshold=5, timeout=30.0)
    detect_retry = RetryPolicy(max_attempts=3, base_delay=1.0)
    health_monitor = HealthMonitor()
"""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitBreakerState,
    CircuitBreakerTimeout,
)
from .retry import (
    RetryPolicy,
    MaxRetriesExceeded,
)
from .health_monitor import (
    HealthMonitor,
    HealthStatus,
    HealthCheckResult,
    HealthReport,
)

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "CircuitBreakerState",
    "CircuitBreakerTimeout",
    # Retry Policy
    "RetryPolicy",
    "MaxRetriesExceeded",
    # Health Monitor
    "HealthMonitor",
    "HealthStatus",
    "HealthCheckResult",
    "HealthReport",
]
