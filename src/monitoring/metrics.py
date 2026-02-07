"""
Metrics Collection System

Thread-safe metrics collection for performance monitoring,
with percentile calculations and statistical analysis.

Example:
    from src.monitoring.metrics import MetricsCollector

    metrics = MetricsCollector()

    # Record latencies
    with metrics.timer("detection_latency"):
        detections = detector.detect(frame)

    # Record events
    metrics.increment("ptz_movements")
    metrics.increment("detection_failures")

    # Get statistics
    stats = metrics.get_stats()
    print(f"Detection p99: {stats['detection_latency']['p99']:.3f}s")
"""

import threading
import time
import logging
from typing import Dict, List, Optional, Any, ContextManager
from dataclasses import dataclass, field
from collections import defaultdict
from contextlib import contextmanager
from statistics import median, mean
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class LatencyMetrics:
    """Latency metrics with percentile calculations."""
    samples: List[float] = field(default_factory=list)
    count: int = 0
    min: float = float('inf')
    max: float = 0.0
    mean: float = 0.0
    median: float = 0.0
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0

    def update(self, value: float) -> None:
        """Add sample and recalculate stats."""
        self.samples.append(value)
        self.count += 1
        self.min = min(self.min, value)
        self.max = max(self.max, value)
        self._recalculate()

    def _recalculate(self) -> None:
        """Recalculate all statistics."""
        if not self.samples:
            return

        self.mean = mean(self.samples)
        self.median = median(self.samples)

        sorted_samples = sorted(self.samples)
        n = len(sorted_samples)

        # Percentile calculations
        self.p50 = sorted_samples[max(0, int(n * 0.50) - 1)]
        self.p95 = sorted_samples[max(0, int(n * 0.95) - 1)]
        self.p99 = sorted_samples[max(0, int(n * 0.99) - 1)]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "count": self.count,
            "min": f"{self.min:.4f}s",
            "max": f"{self.max:.4f}s",
            "mean": f"{self.mean:.4f}s",
            "median": f"{self.median:.4f}s",
            "p50": f"{self.p50:.4f}s",
            "p95": f"{self.p95:.4f}s",
            "p99": f"{self.p99:.4f}s",
        }


@dataclass
class CounterMetrics:
    """Simple counter metrics."""
    value: int = 0
    timestamp: float = field(default_factory=time.time)

    def increment(self, amount: int = 1) -> None:
        """Increment counter."""
        self.value += amount
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "value": self.value,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
        }


class MetricsCollector:
    """
    Thread-safe metrics collector for system monitoring.

    Tracks:
    - Latencies with percentile calculations
    - Event counters
    - Error rates
    - Custom metrics

    Attributes:
        name: Collector identifier
        max_samples: Maximum samples to keep per metric (memory management)
    """

    def __init__(
        self,
        name: str = "MetricsCollector",
        max_samples: int = 10000
    ):
        """
        Initialize metrics collector.

        Args:
            name: Collector identifier (default: "MetricsCollector")
            max_samples: Max samples per latency metric (default: 10000)
        """
        self.name = name
        self.max_samples = max_samples

        self._latencies: Dict[str, LatencyMetrics] = defaultdict(LatencyMetrics)
        self._counters: Dict[str, CounterMetrics] = defaultdict(
            lambda: CounterMetrics()
        )
        self._lock = threading.RLock()
        self._start_time = time.time()

        logger.debug(f"[{self.name}] Initialized")

    def record_latency(self, metric_name: str, duration: float) -> None:
        """
        Record a latency measurement.

        Args:
            metric_name: Name of the latency metric
            duration: Duration in seconds
        """
        with self._lock:
            metrics = self._latencies[metric_name]
            metrics.update(duration)

            # Keep memory bounded
            if len(metrics.samples) > self.max_samples:
                # Keep only most recent samples
                metrics.samples = metrics.samples[-self.max_samples:]
                metrics._recalculate()

    def increment(self, metric_name: str, amount: int = 1) -> None:
        """
        Increment a counter metric.

        Args:
            metric_name: Name of the counter
            amount: Increment amount (default: 1)
        """
        with self._lock:
            self._counters[metric_name].increment(amount)

    def set_counter(self, metric_name: str, value: int) -> None:
        """
        Set counter to specific value.

        Args:
            metric_name: Name of the counter
            value: New value
        """
        with self._lock:
            self._counters[metric_name].value = value
            self._counters[metric_name].timestamp = time.time()

    @contextmanager
    def timer(self, metric_name: str) -> ContextManager:
        """
        Context manager for timing operations.

        Args:
            metric_name: Name of the latency metric

        Yields:
            Context manager

        Example:
            with metrics.timer("operation_latency"):
                do_something()
        """
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.record_latency(metric_name, duration)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get all metrics in dictionary form.

        Returns:
            Dictionary with latency and counter stats
        """
        with self._lock:
            stats = {
                "timestamp": datetime.now().isoformat(),
                "uptime": f"{time.time() - self._start_time:.1f}s",
                "latencies": {
                    name: metrics.to_dict()
                    for name, metrics in self._latencies.items()
                },
                "counters": {
                    name: counter.to_dict()
                    for name, counter in self._counters.items()
                }
            }

        return stats

    def get_latency_stats(self, metric_name: str) -> Optional[dict]:
        """
        Get statistics for a specific latency metric.

        Args:
            metric_name: Name of the metric

        Returns:
            Dictionary with stats or None if not found
        """
        with self._lock:
            if metric_name in self._latencies:
                return self._latencies[metric_name].to_dict()
        return None

    def get_counter(self, metric_name: str) -> Optional[int]:
        """
        Get current value of a counter.

        Args:
            metric_name: Name of the counter

        Returns:
            Counter value or None if not found
        """
        with self._lock:
            if metric_name in self._counters:
                return self._counters[metric_name].value
        return None

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of key metrics.

        Returns:
            Dictionary with important metrics only
        """
        with self._lock:
            summary = {
                "timestamp": datetime.now().isoformat(),
                "uptime": f"{time.time() - self._start_time:.1f}s",
                "latency_metrics": list(self._latencies.keys()),
                "counter_metrics": list(self._counters.keys()),
                "total_latency_samples": sum(
                    m.count for m in self._latencies.values()
                ),
                "total_events": sum(
                    c.value for c in self._counters.values()
                ),
            }

        return summary

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._latencies.clear()
            self._counters.clear()
            self._start_time = time.time()
        logger.info(f"[{self.name}] Metrics reset")

    def reset_metric(self, metric_name: str) -> None:
        """
        Reset specific metric.

        Args:
            metric_name: Name of the metric to reset
        """
        with self._lock:
            if metric_name in self._latencies:
                del self._latencies[metric_name]
            if metric_name in self._counters:
                del self._counters[metric_name]
        logger.debug(f"[{self.name}] Reset metric: {metric_name}")

    def get_metric_names(self) -> tuple[List[str], List[str]]:
        """
        Get all metric names.

        Returns:
            Tuple of (latency_names, counter_names)
        """
        with self._lock:
            return list(self._latencies.keys()), list(self._counters.keys())
