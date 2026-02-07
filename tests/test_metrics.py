"""
Tests for Metrics Collection System.

Tests metrics collection:
- Latency recording and percentile calculations
- Counter metrics
- Thread safety
- Statistics retrieval
"""

import pytest
import threading
import time
from src.monitoring.metrics import MetricsCollector


class TestMetricsLatencyRecording:
    """Test latency metric recording."""
    
    def test_record_single_latency(self):
        """Should record a single latency."""
        collector = MetricsCollector()
        
        collector.record_latency("operation_time", 0.5)
        
        stats = collector.get_latency_stats("operation_time")
        assert stats["count"] == 1
        assert stats["min"] == "0.5000s"
        assert stats["max"] == "0.5000s"
    
    def test_record_multiple_latencies(self):
        """Should record multiple latencies."""
        collector = MetricsCollector()
        
        for latency in [0.1, 0.2, 0.3, 0.4, 0.5]:
            collector.record_latency("operation", latency)
        
        stats = collector.get_latency_stats("operation")
        assert stats["count"] == 5
    
    def test_min_max_tracking(self):
        """Should track min and max latencies."""
        collector = MetricsCollector()
        
        for latency in [0.5, 0.1, 0.8, 0.2]:
            collector.record_latency("op", latency)
        
        stats = collector.get_latency_stats("op")
        assert "0.1000s" in stats["min"]
        assert "0.8000s" in stats["max"]
    
    def test_mean_calculation(self):
        """Should calculate mean latency."""
        collector = MetricsCollector()
        
        for latency in [0.1, 0.2, 0.3]:
            collector.record_latency("op", latency)
        
        stats = collector.get_latency_stats("op")
        # Mean should be 0.2
        assert "0.2000s" in stats["mean"]
    
    def test_percentile_calculations(self):
        """Should calculate percentiles."""
        collector = MetricsCollector()
        
        # Create 100 samples
        for i in range(100):
            collector.record_latency("latency", i / 100.0)
        
        stats = collector.get_latency_stats("latency")
        
        # Should have p50, p95, p99
        assert "p50" in stats
        assert "p95" in stats
        assert "p99" in stats
    
    def test_percentile_ordering(self):
        """Percentiles should be in correct order."""
        collector = MetricsCollector()
        
        for i in range(100):
            collector.record_latency("latency", i / 100.0)
        
        stats = collector.get_latency_stats("latency")
        
        p50_val = float(stats["p50"].rstrip('s'))
        p95_val = float(stats["p95"].rstrip('s'))
        p99_val = float(stats["p99"].rstrip('s'))
        
        # p50 < p95 < p99
        assert p50_val <= p95_val <= p99_val


class TestMetricsCounters:
    """Test counter metrics."""
    
    def test_increment_counter(self):
        """Should increment counter."""
        collector = MetricsCollector()
        
        collector.increment("operations")
        
        value = collector.get_counter("operations")
        assert value == 1
    
    def test_increment_by_amount(self):
        """Should increment by specified amount."""
        collector = MetricsCollector()
        
        collector.increment("count", 5)
        
        value = collector.get_counter("count")
        assert value == 5
    
    def test_multiple_increments(self):
        """Should accumulate increments."""
        collector = MetricsCollector()
        
        collector.increment("count")
        collector.increment("count")
        collector.increment("count", 3)
        
        value = collector.get_counter("count")
        assert value == 5
    
    def test_set_counter_value(self):
        """Should set counter to specific value."""
        collector = MetricsCollector()
        
        collector.set_counter("level", 10)
        
        value = collector.get_counter("level")
        assert value == 10
    
    def test_set_overwrites_previous(self):
        """set_counter should overwrite previous value."""
        collector = MetricsCollector()
        
        collector.increment("count", 5)
        collector.set_counter("count", 10)
        
        value = collector.get_counter("count")
        assert value == 10


class TestMetricsTimer:
    """Test timer context manager."""
    
    def test_timer_context_manager(self):
        """Should use timer context manager."""
        collector = MetricsCollector()
        
        with collector.timer("operation"):
            time.sleep(0.01)
        
        stats = collector.get_latency_stats("operation")
        assert stats["count"] == 1
    
    def test_timer_records_duration(self):
        """Timer should record actual duration."""
        collector = MetricsCollector()
        
        with collector.timer("sleep"):
            time.sleep(0.02)
        
        stats = collector.get_latency_stats("sleep")
        duration = float(stats["min"].rstrip('s'))
        assert duration >= 0.01


class TestMetricsThreadSafety:
    """Test thread-safe metrics collection."""
    
    def test_concurrent_latency_recording(self):
        """Should handle concurrent latency recording."""
        collector = MetricsCollector()
        
        def record_metrics():
            for i in range(100):
                collector.record_latency("latency", i / 100.0)
        
        threads = [threading.Thread(target=record_metrics) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        stats = collector.get_latency_stats("latency")
        assert stats["count"] == 500
    
    def test_concurrent_counter_increment(self):
        """Should handle concurrent counter increments."""
        collector = MetricsCollector()
        
        def increment_counter():
            for _ in range(100):
                collector.increment("counter")
        
        threads = [threading.Thread(target=increment_counter) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        value = collector.get_counter("counter")
        assert value == 500
    
    def test_concurrent_mixed_operations(self):
        """Should handle mixed concurrent operations."""
        collector = MetricsCollector()
        
        def mixed_ops():
            for i in range(50):
                collector.record_latency("latency", i / 100.0)
                collector.increment("counter")
        
        threads = [threading.Thread(target=mixed_ops) for _ in range(3)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        latency_stats = collector.get_latency_stats("latency")
        counter_value = collector.get_counter("counter")
        
        assert latency_stats["count"] == 150
        assert counter_value == 150


class TestMetricsStatistics:
    """Test statistics retrieval."""
    
    def test_get_stats_includes_all_metrics(self):
        """get_stats should include all metrics."""
        collector = MetricsCollector()
        
        collector.record_latency("latency1", 0.1)
        collector.record_latency("latency2", 0.2)
        collector.increment("counter1")
        collector.increment("counter2", 5)
        
        stats = collector.get_stats()
        
        assert "timestamp" in stats
        assert "uptime" in stats
        assert "latencies" in stats
        assert "counters" in stats
        assert "latency1" in stats["latencies"]
        assert "latency2" in stats["latencies"]
        assert "counter1" in stats["counters"]
        assert "counter2" in stats["counters"]
    
    def test_get_summary(self):
        """get_summary should return summary info."""
        collector = MetricsCollector()
        
        collector.record_latency("op1", 0.1)
        collector.record_latency("op2", 0.2)
        collector.increment("event1")
        collector.increment("event2", 5)
        
        summary = collector.get_summary()
        
        assert "timestamp" in summary
        assert "uptime" in summary
        assert "latency_metrics" in summary
        assert "counter_metrics" in summary
        assert len(summary["latency_metrics"]) == 2
        assert len(summary["counter_metrics"]) == 2
        assert summary["total_latency_samples"] == 2
        assert summary["total_events"] == 6
    
    def test_metric_names_retrieval(self):
        """Should retrieve all metric names."""
        collector = MetricsCollector()
        
        collector.record_latency("latency1", 0.1)
        collector.record_latency("latency2", 0.2)
        collector.increment("counter1")
        
        latency_names, counter_names = collector.get_metric_names()
        
        assert "latency1" in latency_names
        assert "latency2" in latency_names
        assert "counter1" in counter_names


class TestMetricsReset:
    """Test metrics reset functionality."""
    
    def test_reset_all_metrics(self):
        """Should reset all metrics."""
        collector = MetricsCollector()
        
        collector.record_latency("latency", 0.1)
        collector.increment("counter")
        
        collector.reset()
        
        assert collector.get_latency_stats("latency") is None
        assert collector.get_counter("counter") is None
    
    def test_reset_specific_metric(self):
        """Should reset specific metric."""
        collector = MetricsCollector()
        
        collector.record_latency("latency1", 0.1)
        collector.record_latency("latency2", 0.2)
        collector.increment("counter")
        
        collector.reset_metric("latency1")
        
        assert collector.get_latency_stats("latency1") is None
        assert collector.get_latency_stats("latency2") is not None
        assert collector.get_counter("counter") is not None


class TestMetricsMemoryManagement:
    """Test memory management with max_samples."""
    
    def test_max_samples_enforcement(self):
        """Should not keep more than max_samples."""
        collector = MetricsCollector(max_samples=100)
        
        # Record 200 samples
        for i in range(200):
            collector.record_latency("latency", i / 100.0)
        
        stats = collector.get_latency_stats("latency")
        assert stats["count"] == 200  # Count still accurate
        
        # But only ~100 samples kept in memory
        assert len(collector._latencies["latency"].samples) <= 105  # Some margin


class TestMetricsUptime:
    """Test uptime tracking."""
    
    def test_uptime_increases(self):
        """Uptime should increase over time."""
        collector = MetricsCollector()
        
        stats1 = collector.get_stats()
        time.sleep(0.1)
        stats2 = collector.get_stats()
        
        uptime1 = float(stats1["uptime"].rstrip('s'))
        uptime2 = float(stats2["uptime"].rstrip('s'))
        
        assert uptime2 > uptime1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
