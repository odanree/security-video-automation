"""
Tests for Circuit Breaker pattern implementation.

Tests all state transitions and failure handling:
- CLOSED → OPEN on failure threshold
- OPEN → HALF_OPEN on timeout
- HALF_OPEN → CLOSED on success threshold
- HALF_OPEN → OPEN on failure
"""

import pytest
import time
from src.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitBreakerState,
)


class TestCircuitBreakerStateMachine:
    """Test circuit breaker state transitions."""
    
    def test_initial_state_is_closed(self):
        """Circuit breaker should start in CLOSED state."""
        breaker = CircuitBreaker(failure_threshold=3)
        assert breaker.state == CircuitBreakerState.CLOSED
    
    def test_closed_to_open_transition(self):
        """Circuit should open after reaching failure threshold."""
        breaker = CircuitBreaker(failure_threshold=2)
        
        def failing_func():
            raise ValueError("Test failure")
        
        # First failure - still CLOSED
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.metrics.failure_count == 1
        
        # Second failure - should transition to OPEN
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.metrics.failure_count == 2
    
    def test_open_rejects_calls(self):
        """Circuit should reject calls when OPEN."""
        breaker = CircuitBreaker(failure_threshold=1)
        
        def failing_func():
            raise ValueError("Test failure")
        
        # Open the circuit
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        
        # Now circuit is open - should reject without calling func
        with pytest.raises(CircuitBreakerOpen):
            breaker.call(failing_func)
        
        # Rejection count should increase
        assert breaker.metrics.total_rejections == 1
    
    def test_open_to_half_open_transition(self):
        """Circuit should attempt recovery after timeout."""
        breaker = CircuitBreaker(
            failure_threshold=1,
            timeout=0.5,  # 500ms timeout
            success_threshold=1  # One success should close
        )
        
        def failing_func():
            raise ValueError("Test failure")
        
        # Open the circuit
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.state == CircuitBreakerState.OPEN
        
        # Immediately - still OPEN
        with pytest.raises(CircuitBreakerOpen):
            breaker.call(failing_func)
        
        # Wait for timeout
        time.sleep(0.6)
        
        # Next call should attempt recovery (HALF_OPEN) and succeed
        def success_func():
            return "success"
        
        result = breaker.call(success_func)
        assert result == "success"
        # After success_threshold successes in HALF_OPEN, should be CLOSED
        assert breaker.state == CircuitBreakerState.CLOSED
    
    def test_half_open_to_closed_on_success(self):
        """Circuit should close after success threshold in HALF_OPEN."""
        breaker = CircuitBreaker(
            failure_threshold=1,
            timeout=0.1,
            success_threshold=2
        )
        
        def failing_func():
            raise ValueError("Test failure")
        
        def success_func():
            return "ok"
        
        # Open circuit
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.state == CircuitBreakerState.OPEN
        
        # Wait and attempt recovery
        time.sleep(0.2)
        
        # First success moves to HALF_OPEN and increments success_count
        result = breaker.call(success_func)
        assert result == "ok"
        assert breaker.state == CircuitBreakerState.HALF_OPEN
        
        # Second success closes circuit
        result = breaker.call(success_func)
        assert result == "ok"
        assert breaker.state == CircuitBreakerState.CLOSED
        # Total successes should be 2 (from HALF_OPEN recovery)
        assert breaker.metrics.total_successes == 2
    
    def test_half_open_to_open_on_failure(self):
        """Circuit should reopen if fails during HALF_OPEN."""
        breaker = CircuitBreaker(
            failure_threshold=1,
            timeout=0.1
        )
        
        def failing_func():
            raise ValueError("Test failure")
        
        def success_func():
            return "ok"
        
        # Open circuit
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        
        # Wait and attempt recovery
        time.sleep(0.2)
        
        # Attempt recovery should succeed
        result = breaker.call(success_func)
        assert result == "ok"
        assert breaker.state == CircuitBreakerState.HALF_OPEN
        
        # But then fail
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.state == CircuitBreakerState.OPEN


class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator usage."""
    
    def test_decorator_wraps_function(self):
        """Decorator should wrap function with circuit breaker."""
        breaker = CircuitBreaker(failure_threshold=2)
        
        @breaker
        def calculate(x, y):
            return x + y
        
        result = calculate(2, 3)
        assert result == 5
        assert breaker.metrics.total_calls == 1
    
    def test_decorator_tracks_failures(self):
        """Decorator should track failures properly."""
        breaker = CircuitBreaker(failure_threshold=1)
        
        @breaker
        def failing_func():
            raise ValueError("Error")
        
        with pytest.raises(ValueError):
            failing_func()
        
        assert breaker.metrics.failure_count == 1
        
        # Should open on second attempt
        with pytest.raises(CircuitBreakerOpen):
            failing_func()


class TestCircuitBreakerMetrics:
    """Test circuit breaker metrics and monitoring."""
    
    def test_get_status_returns_complete_info(self):
        """get_status should return all relevant metrics."""
        breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=30.0,
            name="test_breaker"
        )
        
        status = breaker.get_status()
        
        assert status["name"] == "test_breaker"
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["failure_threshold"] == 5
        assert status["timeout"] == 30.0
        assert "last_state_change" in status
    
    def test_metrics_track_rejections(self):
        """Circuit breaker should track rejection count."""
        breaker = CircuitBreaker(failure_threshold=1, timeout=10)
        
        def failing_func():
            raise ValueError("Error")
        
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        
        # Open now
        assert breaker.state == CircuitBreakerState.OPEN
        
        # Try to call - should be rejected
        with pytest.raises(CircuitBreakerOpen):
            breaker.call(failing_func)
        
        assert breaker.metrics.total_rejections == 1
        
        # Another rejection
        with pytest.raises(CircuitBreakerOpen):
            breaker.call(failing_func)
        
        assert breaker.metrics.total_rejections == 2
    
    def test_metrics_track_successes_in_closed(self):
        """Circuit breaker should track total successes."""
        breaker = CircuitBreaker()
        
        def success_func():
            return "ok"
        
        for _ in range(5):
            breaker.call(success_func)
        
        assert breaker.metrics.total_successes == 5
        assert breaker.metrics.total_calls == 5


class TestCircuitBreakerReset:
    """Test circuit breaker reset functionality."""
    
    def test_manual_reset(self):
        """Manual reset should close circuit."""
        breaker = CircuitBreaker(failure_threshold=1)
        
        def failing_func():
            raise ValueError("Error")
        
        # Open circuit
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.state == CircuitBreakerState.OPEN
        
        # Reset
        breaker.reset()
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.metrics.failure_count == 0
    
    def test_reset_clears_metrics(self):
        """Reset should clear failure count."""
        breaker = CircuitBreaker(failure_threshold=2)
        
        def failing_func():
            raise ValueError("Error")
        
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        
        assert breaker.metrics.failure_count == 1
        
        breaker.reset()
        assert breaker.metrics.failure_count == 0


class TestCircuitBreakerEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_failure_count_resets_on_success(self):
        """Failure count should reset after success in CLOSED state."""
        breaker = CircuitBreaker(failure_threshold=3)
        
        def failing_func():
            raise ValueError("Error")
        
        def success_func():
            return "ok"
        
        # One failure
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.metrics.failure_count == 1
        
        # Success should reset failure count
        breaker.call(success_func)
        assert breaker.metrics.failure_count == 0
    
    def test_circuit_tracks_call_count(self):
        """Circuit breaker should track total calls."""
        breaker = CircuitBreaker()
        
        def func(x):
            return x
        
        for i in range(10):
            breaker.call(func, i)
        
        assert breaker.metrics.total_calls == 10
    
    def test_expected_exception_filtering(self):
        """Circuit should only count expected exception types."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            expected_exception=ValueError
        )
        
        def value_error_func():
            raise ValueError("Value error")
        
        def type_error_func():
            raise TypeError("Type error")
        
        # ValueError should count as failure
        with pytest.raises(ValueError):
            breaker.call(value_error_func)
        assert breaker.metrics.failure_count == 1
        
        # TypeError should NOT count as failure (pass through)
        with pytest.raises(TypeError):
            breaker.call(type_error_func)
        assert breaker.metrics.failure_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
