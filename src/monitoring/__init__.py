"""
Monitoring Layer

System metrics collection and analysis:
- Thread-safe metrics collection
- Latency tracking with percentiles
- Event counting
- Performance statistics

Example:
    from src.monitoring import MetricsCollector

    metrics = MetricsCollector()

    with metrics.timer("operation_latency"):
        result = process_frame()

    metrics.increment("successful_operations")
"""

from .metrics import (
    MetricsCollector,
    LatencyMetrics,
    CounterMetrics,
)

__all__ = [
    "MetricsCollector",
    "LatencyMetrics",
    "CounterMetrics",
]
