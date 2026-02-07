"""
Tests for Health Monitoring System.

Tests health check functionality:
- Health check registration
- Check execution and status
- Alert generation
- Status aggregation
"""

import pytest
import asyncio
from src.resilience.health_monitor import (
    HealthMonitor,
    HealthStatus,
    HealthCheckResult,
)


class TestHealthMonitorRegistration:
    """Test health check registration."""
    
    def test_register_check(self):
        """Should register health checks."""
        monitor = HealthMonitor()
        
        async def check_func():
            return HealthStatus.HEALTHY
        
        monitor.register_check("test_check", check_func, "Test check")
        
        assert "test_check" in monitor._checks
        assert "test_check" in monitor._check_messages
    
    def test_register_multiple_checks(self):
        """Should register multiple checks."""
        monitor = HealthMonitor()
        
        async def check1():
            return HealthStatus.HEALTHY
        
        async def check2():
            return HealthStatus.HEALTHY
        
        monitor.register_check("check1", check1)
        monitor.register_check("check2", check2)
        
        assert len(monitor._checks) == 2


class TestHealthMonitorExecution:
    """Test health check execution."""
    
    @pytest.mark.asyncio
    async def test_run_single_check(self):
        """Should run a single health check."""
        monitor = HealthMonitor()
        
        async def healthy_check():
            return HealthStatus.HEALTHY
        
        monitor.register_check("test", healthy_check)
        report = await monitor.run_checks()
        
        assert report.overall == HealthStatus.HEALTHY
        assert len(report.checks) == 1
        assert report.checks[0].status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_run_multiple_checks(self):
        """Should run multiple checks."""
        monitor = HealthMonitor()
        
        async def healthy_check1():
            return HealthStatus.HEALTHY
        
        async def healthy_check2():
            return HealthStatus.HEALTHY
        
        monitor.register_check("check1", healthy_check1)
        monitor.register_check("check2", healthy_check2)
        
        report = await monitor.run_checks()
        
        assert len(report.checks) == 2
        assert report.overall == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_check_with_failure(self):
        """Should handle check failures."""
        monitor = HealthMonitor()
        
        async def failing_check():
            return HealthStatus.UNHEALTHY
        
        monitor.register_check("failing", failing_check)
        report = await monitor.run_checks()
        
        assert report.checks[0].status == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_check_with_exception(self):
        """Should handle exceptions in checks."""
        monitor = HealthMonitor()
        
        async def error_check():
            raise ValueError("Test error")
        
        monitor.register_check("error", error_check)
        report = await monitor.run_checks()
        
        assert report.checks[0].status == HealthStatus.UNHEALTHY
        assert "error" in report.checks[0].error.lower()
    
    @pytest.mark.asyncio
    async def test_check_timeout(self):
        """Should timeout long-running checks."""
        monitor = HealthMonitor(timeout=0.1)
        
        async def slow_check():
            await asyncio.sleep(1.0)
            return HealthStatus.HEALTHY
        
        monitor.register_check("slow", slow_check)
        report = await monitor.run_checks()
        
        assert report.checks[0].status == HealthStatus.UNHEALTHY
        assert "timed out" in report.checks[0].error.lower()


class TestHealthMonitorAggregation:
    """Test health status aggregation."""
    
    @pytest.mark.asyncio
    async def test_all_healthy_aggregation(self):
        """Should aggregate to HEALTHY when all checks pass."""
        monitor = HealthMonitor()
        
        async def check1():
            return HealthStatus.HEALTHY
        
        async def check2():
            return HealthStatus.HEALTHY
        
        monitor.register_check("check1", check1)
        monitor.register_check("check2", check2)
        
        report = await monitor.run_checks()
        assert report.overall == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_degraded_aggregation(self):
        """Should aggregate to DEGRADED if any check is degraded."""
        monitor = HealthMonitor()
        
        async def healthy():
            return HealthStatus.HEALTHY
        
        async def degraded():
            return HealthStatus.DEGRADED
        
        monitor.register_check("healthy", healthy)
        monitor.register_check("degraded", degraded)
        
        report = await monitor.run_checks()
        assert report.overall == HealthStatus.DEGRADED
    
    @pytest.mark.asyncio
    async def test_unhealthy_aggregation(self):
        """Should aggregate to UNHEALTHY if any check fails."""
        monitor = HealthMonitor()
        
        async def healthy():
            return HealthStatus.HEALTHY
        
        async def unhealthy():
            return HealthStatus.UNHEALTHY
        
        monitor.register_check("healthy", healthy)
        monitor.register_check("unhealthy", unhealthy)
        
        report = await monitor.run_checks()
        assert report.overall == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_unhealthy_takes_priority(self):
        """UNHEALTHY should take priority over DEGRADED."""
        monitor = HealthMonitor()
        
        async def healthy():
            return HealthStatus.HEALTHY
        
        async def degraded():
            return HealthStatus.DEGRADED
        
        async def unhealthy():
            return HealthStatus.UNHEALTHY
        
        monitor.register_check("h", healthy)
        monitor.register_check("d", degraded)
        monitor.register_check("u", unhealthy)
        
        report = await monitor.run_checks()
        assert report.overall == HealthStatus.UNHEALTHY


class TestHealthMonitorAlerts:
    """Test alert generation."""
    
    @pytest.mark.asyncio
    async def test_alerts_on_unhealthy(self):
        """Should generate alerts for unhealthy checks."""
        monitor = HealthMonitor()
        
        async def unhealthy():
            return HealthStatus.UNHEALTHY
        
        monitor.register_check("critical_service", unhealthy)
        report = await monitor.run_checks()
        
        assert len(report.alerts) > 0
        assert "critical_service" in report.alerts[1].lower()
    
    @pytest.mark.asyncio
    async def test_alerts_on_degraded_if_enabled(self):
        """Should generate alerts for degraded if alert_on_degraded=True."""
        monitor = HealthMonitor(alert_on_degraded=True)
        
        async def degraded():
            return HealthStatus.DEGRADED
        
        monitor.register_check("service", degraded)
        report = await monitor.run_checks()
        
        # Should have degraded alert
        assert any("degraded" in alert.lower() for alert in report.alerts)
    
    @pytest.mark.asyncio
    async def test_no_alerts_when_healthy(self):
        """Should not generate alerts when all healthy."""
        monitor = HealthMonitor()
        
        async def healthy():
            return HealthStatus.HEALTHY
        
        monitor.register_check("service", healthy)
        report = await monitor.run_checks()
        
        assert len(report.alerts) == 0
    
    @pytest.mark.asyncio
    async def test_system_health_critical_alert(self):
        """Should emit system-level critical alert."""
        monitor = HealthMonitor()
        
        async def unhealthy():
            return HealthStatus.UNHEALTHY
        
        monitor.register_check("service", unhealthy)
        report = await monitor.run_checks()
        
        # First alert should be system-level
        assert "critical" in report.alerts[0].lower() or "system" in report.alerts[0].lower()


class TestHealthMonitorHistory:
    """Test check history tracking."""
    
    @pytest.mark.asyncio
    async def test_store_check_history(self):
        """Should store check history."""
        monitor = HealthMonitor()
        
        async def check():
            return HealthStatus.HEALTHY
        
        monitor.register_check("test", check)
        
        await monitor.run_checks()
        await monitor.run_checks()
        
        history = monitor.get_check_history("test")
        assert len(history) == 2
    
    @pytest.mark.asyncio
    async def test_history_limit(self):
        """Should respect history limit."""
        monitor = HealthMonitor()
        
        async def check():
            return HealthStatus.HEALTHY
        
        monitor.register_check("test", check)
        
        for _ in range(15):
            await monitor.run_checks()
        
        history = monitor.get_check_history("test", limit=10)
        assert len(history) == 10
    
    @pytest.mark.asyncio
    async def test_reset_history(self):
        """Should reset history."""
        monitor = HealthMonitor()
        
        async def check():
            return HealthStatus.HEALTHY
        
        monitor.register_check("test", check)
        
        await monitor.run_checks()
        
        assert len(monitor.get_check_history("test")) == 1
        
        monitor.reset_history()
        
        assert len(monitor.get_check_history("test")) == 0


class TestHealthMonitorReports:
    """Test health reports."""
    
    @pytest.mark.asyncio
    async def test_last_report_storage(self):
        """Should store last report."""
        monitor = HealthMonitor()
        
        async def check():
            return HealthStatus.HEALTHY
        
        monitor.register_check("test", check)
        report1 = await monitor.run_checks()
        
        assert monitor.get_last_report() == report1
    
    @pytest.mark.asyncio
    async def test_report_to_dict(self):
        """Report should convert to dict."""
        monitor = HealthMonitor()
        
        async def check():
            return HealthStatus.HEALTHY
        
        monitor.register_check("test", check, "Test check message")
        report = await monitor.run_checks()
        
        report_dict = report.to_dict()
        
        assert "overall" in report_dict
        assert "timestamp" in report_dict
        assert "checks" in report_dict
        assert "alerts" in report_dict
        assert len(report_dict["checks"]) == 1
    
    @pytest.mark.asyncio
    async def test_check_result_to_dict(self):
        """Check result should convert to dict."""
        monitor = HealthMonitor()
        
        async def check():
            return HealthStatus.HEALTHY
        
        monitor.register_check("test", check)
        report = await monitor.run_checks()
        
        check_dict = report.checks[0].to_dict()
        
        assert "name" in check_dict
        assert "status" in check_dict
        assert "duration" in check_dict
        assert "timestamp" in check_dict


class TestHealthMonitorTiming:
    """Test timing and duration tracking."""
    
    @pytest.mark.asyncio
    async def test_check_duration_tracking(self):
        """Should track check duration."""
        monitor = HealthMonitor()
        
        async def slow_check():
            await asyncio.sleep(0.05)
            return HealthStatus.HEALTHY
        
        monitor.register_check("slow", slow_check)
        report = await monitor.run_checks()
        
        assert report.checks[0].duration >= 0.05
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_checks(self):
        """Multiple checks should run concurrently."""
        monitor = HealthMonitor()
        
        async def check1():
            await asyncio.sleep(0.05)
            return HealthStatus.HEALTHY
        
        async def check2():
            await asyncio.sleep(0.05)
            return HealthStatus.HEALTHY
        
        monitor.register_check("check1", check1)
        monitor.register_check("check2", check2)
        
        start = asyncio.get_event_loop().time()
        report = await monitor.run_checks()
        elapsed = asyncio.get_event_loop().time() - start
        
        # Should be ~0.05s (parallel) not ~0.10s (serial)
        assert elapsed < 0.08


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
