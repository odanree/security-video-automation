"""
Tests for Retry Policy with exponential backoff.

Tests retry logic:
- Successful retry after failures
- Max attempts exceeded
- Exponential backoff timing
- Jitter application
"""

import pytest
import asyncio
import time
from src.resilience.retry import (
    RetryPolicy,
    MaxRetriesExceeded,
)


class TestRetryPolicyBasic:
    """Test basic retry functionality."""
    
    def test_success_on_first_attempt(self):
        """Should succeed immediately if no errors."""
        policy = RetryPolicy(max_attempts=3)
        
        def success_func():
            return "success"
        
        result = policy(success_func)
        assert result == "success"
        assert policy.metrics.total_attempts == 1
        assert policy.metrics.total_successes == 1
        assert policy.metrics.total_failures == 0
    
    def test_success_after_failures(self):
        """Should retry and eventually succeed."""
        policy = RetryPolicy(max_attempts=3, base_delay=0.01)
        
        attempt_count = 0
        
        def eventual_success():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError(f"Attempt {attempt_count}")
            return "success"
        
        result = policy(eventual_success)
        assert result == "success"
        assert attempt_count == 3
        assert policy.metrics.total_successes == 1
        assert policy.metrics.total_failures == 2
    
    def test_max_retries_exceeded(self):
        """Should raise MaxRetriesExceeded when all attempts fail."""
        policy = RetryPolicy(max_attempts=2, base_delay=0.001)
        
        def always_fails():
            raise ValueError("Always fails")
        
        with pytest.raises(MaxRetriesExceeded):
            policy(always_fails)
        
        assert policy.metrics.total_attempts == 2
        assert policy.metrics.total_successes == 0
        assert policy.metrics.total_failures == 2
        assert policy.metrics.retries_exhausted == 1
    
    def test_single_attempt_config(self):
        """Should not retry if max_attempts=1."""
        policy = RetryPolicy(max_attempts=1)
        
        def failing_func():
            raise ValueError("Error")
        
        with pytest.raises(MaxRetriesExceeded):
            policy(failing_func)
        
        assert policy.metrics.total_attempts == 1


class TestRetryPolicyBackoff:
    """Test exponential backoff timing."""
    
    def test_exponential_backoff_calculation(self):
        """Should calculate exponential backoff correctly."""
        policy = RetryPolicy(
            max_attempts=5,
            base_delay=1.0,
            max_delay=100.0,
            jitter=False,
            backoff_multiplier=2.0
        )
        
        # Calculate delays manually
        assert policy._calculate_delay(0) == 1.0      # 1 * (2^0) = 1
        assert policy._calculate_delay(1) == 2.0      # 1 * (2^1) = 2
        assert policy._calculate_delay(2) == 4.0      # 1 * (2^2) = 4
        assert policy._calculate_delay(3) == 8.0      # 1 * (2^3) = 8
        assert policy._calculate_delay(4) == 16.0     # 1 * (2^4) = 16
    
    def test_max_delay_cap(self):
        """Delay should be capped at max_delay."""
        policy = RetryPolicy(
            max_attempts=5,
            base_delay=1.0,
            max_delay=10.0,
            jitter=False,
            backoff_multiplier=2.0
        )
        
        # Should cap at 10
        assert policy._calculate_delay(0) == 1.0
        assert policy._calculate_delay(1) == 2.0
        assert policy._calculate_delay(2) == 4.0
        assert policy._calculate_delay(3) == 8.0
        assert policy._calculate_delay(4) == 10.0     # Capped at max_delay
    
    def test_jitter_adds_randomness(self):
        """Jitter should randomize delay."""
        policy = RetryPolicy(
            base_delay=10.0,
            jitter=True
        )
        
        # Run multiple times - should get different values
        delays = [policy._calculate_delay(1) for _ in range(10)]
        
        # At least some variation
        assert len(set(delays)) > 1
        
        # All should be between 0 and max
        assert all(0 <= d <= 20.0 for d in delays)
    
    def test_no_jitter_consistent_delays(self):
        """Without jitter, delays should be consistent."""
        policy = RetryPolicy(
            base_delay=5.0,
            max_delay=100.0,
            jitter=False
        )
        
        delays = [policy._calculate_delay(1) for _ in range(5)]
        
        # All should be identical
        assert len(set(delays)) == 1
        assert delays[0] == 10.0
    
    def test_actual_wait_time(self):
        """Should actually wait the calculated time."""
        policy = RetryPolicy(
            max_attempts=3,
            base_delay=0.05,
            jitter=False
        )
        
        attempt_count = 0
        
        def fails_twice():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Failed")
            return "ok"
        
        start = time.time()
        result = policy(fails_twice)
        elapsed = time.time() - start
        
        # Should have waited ~0.05 + 0.10 = 0.15 seconds
        # (first retry waits 0.05, second retry waits 0.10)
        assert elapsed >= 0.1  # At least the backoff time


class TestRetryPolicyMetrics:
    """Test retry metrics collection."""
    
    def test_metrics_track_attempts(self):
        """Should track total attempts."""
        policy = RetryPolicy(max_attempts=3, base_delay=0.001)
        
        def fails_once():
            if policy.metrics.total_attempts < 2:
                raise ValueError("Failed")
            return "ok"
        
        result = policy(fails_once)
        assert result == "ok"
        assert policy.metrics.total_attempts == 2
    
    def test_metrics_track_successes(self):
        """Should track successful operations."""
        policy = RetryPolicy()
        
        def success():
            return "ok"
        
        policy(success)
        policy(success)
        
        assert policy.metrics.total_successes == 2
    
    def test_get_metrics_returns_summary(self):
        """get_metrics should return complete metrics summary."""
        policy = RetryPolicy(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0
        )
        
        def func():
            return "ok"
        
        policy(func)
        policy(func)
        
        metrics = policy.get_metrics()
        
        assert "name" in metrics
        assert "total_attempts" in metrics
        assert "total_successes" in metrics
        assert "success_rate" in metrics
        assert metrics["total_attempts"] == 2
        assert metrics["total_successes"] == 2


class TestRetryPolicyAsync:
    """Test async retry functionality."""
    
    @pytest.mark.asyncio
    async def test_async_success(self):
        """Should handle async functions."""
        policy = RetryPolicy()
        
        async def async_func():
            await asyncio.sleep(0.001)
            return "success"
        
        result = await policy.call_async(async_func)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_async_retry_and_succeed(self):
        """Should retry async functions."""
        policy = RetryPolicy(max_attempts=3, base_delay=0.01)
        
        attempt_count = 0
        
        async def async_eventual_success():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Failed")
            await asyncio.sleep(0.001)
            return "success"
        
        result = await policy.call_async(async_eventual_success)
        assert result == "success"
        assert attempt_count == 2
    
    @pytest.mark.asyncio
    async def test_async_max_retries(self):
        """Should fail async functions after max attempts."""
        policy = RetryPolicy(max_attempts=2, base_delay=0.001)
        
        async def async_fails():
            await asyncio.sleep(0.001)
            raise ValueError("Always fails")
        
        with pytest.raises(MaxRetriesExceeded):
            await policy.call_async(async_fails)


class TestRetryPolicyDecorator:
    """Test retry decorator usage."""
    
    def test_decorator_wraps_function(self):
        """Decorator should wrap function."""
        policy = RetryPolicy(max_attempts=3)
        
        @policy.decorator
        def add(x, y):
            return x + y
        
        result = add(2, 3)
        assert result == 5
    
    def test_decorator_handles_retries(self):
        """Decorator should handle retries."""
        policy = RetryPolicy(max_attempts=3, base_delay=0.001)
        
        attempt_count = 0
        
        @policy.decorator
        def eventually_succeeds():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Failed")
            return "success"
        
        result = eventually_succeeds()
        assert result == "success"
        assert attempt_count == 2


class TestRetryPolicyEdgeCases:
    """Test edge cases."""
    
    def test_zero_delay_config(self):
        """Should handle zero delay configuration."""
        policy = RetryPolicy(
            max_attempts=3,
            base_delay=0.0,
            max_delay=0.0,
            jitter=False
        )
        
        delays = [policy._calculate_delay(i) for i in range(3)]
        assert all(d == 0.0 for d in delays)
    
    def test_single_attempt_with_failure(self):
        """Single attempt should fail immediately."""
        policy = RetryPolicy(max_attempts=1)
        
        def fails():
            raise ValueError("Error")
        
        with pytest.raises(MaxRetriesExceeded):
            policy(fails)
        
        assert policy.metrics.total_attempts == 1
        assert policy.metrics.retries_exhausted == 1
    
    def test_policy_name_in_metrics(self):
        """Policy name should be included in metrics."""
        policy = RetryPolicy(name="database_retry")
        
        def func():
            return "ok"
        
        policy(func)
        metrics = policy.get_metrics()
        
        assert metrics["name"] == "database_retry"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
