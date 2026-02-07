"""
Health Monitoring System

Provides health checks, status aggregation, and alert emission
for system components.

Example:
    from src.resilience.health_monitor import HealthMonitor, HealthStatus

    monitor = HealthMonitor()

    async def check_ptz():
        try:
            ptz_controller.pan(0)
            return HealthStatus.HEALTHY
        except Exception:
            return HealthStatus.UNHEALTHY

    monitor.register_check("ptz_controller", check_ptz)

    status = await monitor.run_checks()
    if status.overall == HealthStatus.UNHEALTHY:
        logger.critical("System is unhealthy!")
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Dict, Optional, List, Coroutine, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""
    name: str
    status: HealthStatus
    message: str = ""
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "error": self.error,
            "duration": f"{self.duration:.3f}s",
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
        }


@dataclass
class HealthReport:
    """Overall health report."""
    overall: HealthStatus
    timestamp: float = field(default_factory=time.time)
    checks: List[HealthCheckResult] = field(default_factory=list)
    alerts: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "overall": self.overall.value,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "checks": [check.to_dict() for check in self.checks],
            "alerts": self.alerts,
        }


class HealthMonitor:
    """
    Health monitoring system for application components.

    Tracks health of various components, runs health checks,
    aggregates status, and emits alerts.

    Attributes:
        timeout: Timeout for each health check in seconds
        alert_on_degraded: Whether to alert on degraded status
    """

    def __init__(
        self,
        timeout: float = 5.0,
        alert_on_degraded: bool = False,
        name: str = "HealthMonitor"
    ):
        """
        Initialize health monitor.

        Args:
            timeout: Timeout per check in seconds (default: 5.0)
            alert_on_degraded: Alert on degraded status (default: False)
            name: Monitor identifier (default: "HealthMonitor")
        """
        self.timeout = timeout
        self.alert_on_degraded = alert_on_degraded
        self.name = name

        self._checks: Dict[str, Callable[..., Coroutine[Any, Any, HealthStatus]]] = {}
        self._check_messages: Dict[str, str] = {}
        self._last_report: Optional[HealthReport] = None
        self._check_history: Dict[str, List[HealthCheckResult]] = {}

    def register_check(
        self,
        name: str,
        check_func: Callable[..., Coroutine[Any, Any, HealthStatus]],
        message: str = ""
    ) -> None:
        """
        Register a health check.

        Args:
            name: Check identifier
            check_func: Async function returning HealthStatus
            message: Human-readable description
        """
        self._checks[name] = check_func
        self._check_messages[name] = message
        self._check_history[name] = []
        logger.debug(f"[{self.name}] Registered health check: {name}")

    async def run_checks(self) -> HealthReport:
        """
        Run all registered health checks.

        Returns:
            HealthReport with results and aggregated status
        """
        results: List[HealthCheckResult] = []

        # Run all checks concurrently
        check_tasks = [
            self._run_single_check(name, func)
            for name, func in self._checks.items()
        ]

        results = await asyncio.gather(*check_tasks, return_exceptions=False)

        # Filter out any exceptions that slipped through
        results = [r for r in results if isinstance(r, HealthCheckResult)]

        # Store in history
        for result in results:
            self._check_history[result.name].append(result)

        # Aggregate status
        overall = self._aggregate_status(results)

        # Generate alerts
        alerts = self._generate_alerts(results, overall)

        # Create report
        report = HealthReport(
            overall=overall,
            checks=results,
            alerts=alerts
        )

        self._last_report = report

        # Log results
        self._log_report(report)

        return report

    async def _run_single_check(
        self,
        name: str,
        check_func: Callable[..., Coroutine[Any, Any, HealthStatus]]
    ) -> HealthCheckResult:
        """
        Run a single health check with timeout.

        Args:
            name: Check name
            check_func: Check function

        Returns:
            HealthCheckResult
        """
        start = time.time()
        message = self._check_messages.get(name, "")

        try:
            status = await asyncio.wait_for(
                check_func(),
                timeout=self.timeout
            )
            duration = time.time() - start

            return HealthCheckResult(
                name=name,
                status=status,
                message=message,
                duration=duration
            )

        except asyncio.TimeoutError:
            duration = time.time() - start
            logger.error(f"[{self.name}] Check '{name}' timed out after {duration:.2f}s")

            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=message,
                error=f"Check timed out after {self.timeout}s",
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start
            logger.error(f"[{self.name}] Check '{name}' failed: {e}")

            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=message,
                error=str(e),
                duration=duration
            )

    def _aggregate_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """
        Aggregate individual check results into overall status.

        Priority:
        1. UNHEALTHY (any unhealthy = system unhealthy)
        2. DEGRADED (any degraded = system degraded)
        3. HEALTHY

        Args:
            results: List of check results

        Returns:
            Aggregated HealthStatus
        """
        if not results:
            return HealthStatus.UNKNOWN

        statuses = [r.status for r in results]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def _generate_alerts(
        self,
        results: List[HealthCheckResult],
        overall: HealthStatus
    ) -> List[str]:
        """
        Generate alerts based on check results.

        Args:
            results: List of check results
            overall: Aggregated status

        Returns:
            List of alert messages
        """
        alerts = []

        for result in results:
            if result.status == HealthStatus.UNHEALTHY:
                alert = f"CRITICAL: {result.name} is unhealthy"
                if result.error:
                    alert += f": {result.error}"
                alerts.append(alert)

            elif result.status == HealthStatus.DEGRADED:
                if self.alert_on_degraded:
                    alert = f"WARNING: {result.name} is degraded"
                    if result.error:
                        alert += f": {result.error}"
                    alerts.append(alert)

        if overall == HealthStatus.UNHEALTHY:
            alerts.insert(0, "SYSTEM HEALTH CRITICAL: One or more checks failed")
        elif overall == HealthStatus.DEGRADED and self.alert_on_degraded:
            alerts.insert(0, "SYSTEM HEALTH DEGRADED: Service quality reduced")

        return alerts

    def _log_report(self, report: HealthReport) -> None:
        """Log health report."""
        logger.info(f"[{self.name}] Health check summary: {report.overall.value}")

        for check in report.checks:
            logger.debug(
                f"[{self.name}] {check.name}: {check.status.value} "
                f"({check.duration:.3f}s)"
            )

        for alert in report.alerts:
            logger.warning(f"[{self.name}] {alert}")

    def get_last_report(self) -> Optional[HealthReport]:
        """
        Get most recent health report.

        Returns:
            Last HealthReport or None if no checks run
        """
        return self._last_report

    def get_check_history(
        self,
        name: str,
        limit: int = 10
    ) -> List[HealthCheckResult]:
        """
        Get history for a specific check.

        Args:
            name: Check name
            limit: Maximum results to return

        Returns:
            List of recent check results
        """
        if name not in self._check_history:
            return []

        history = self._check_history[name]
        return history[-limit:] if limit > 0 else history

    def reset_history(self) -> None:
        """Clear all check history."""
        for history in self._check_history.values():
            history.clear()
        logger.info(f"[{self.name}] History cleared")
