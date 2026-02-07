"""
Resilience Layer Documentation

Production-grade resilience patterns for handling failures gracefully.
"""

# RESILIENCE LAYER DOCUMENTATION

## Overview

The resilience layer provides production-grade patterns for handling transient failures, preventing cascading failures, and maintaining system health. It includes three core components:

1. **Circuit Breaker** - Prevents cascading failures by stopping requests to failing services
2. **Retry Policy** - Recovers from transient failures with exponential backoff
3. **Health Monitor** - Tracks system health and generates alerts

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Tracking Engine                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Detection Pipeline                                  │  │
│  │  ┌────────────────┐                                  │  │
│  │  │ RetryPolicy    │ ← Recovers from transient errors │  │
│  │  └────────────────┘                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  PTZ Control Pipeline                                │  │
│  │  ┌────────────────┐                                  │  │
│  │  │ CircuitBreaker │ ← Prevents cascading failures    │  │
│  │  └────────────────┘                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Health Monitoring                                   │  │
│  │  ┌────────────────┐                                  │  │
│  │  │ HealthMonitor  │ ← Tracks system health           │  │
│  │  └────────────────┘                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Metrics Collection                                  │  │
│  │  ┌────────────────┐                                  │  │
│  │  │ MetricsCollector│ ← Tracks performance metrics     │  │
│  │  └────────────────┘                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Circuit Breaker Pattern

### Purpose
Prevents cascading failures by stopping requests to a service that is experiencing issues.

### States

```
      failures > threshold
          │
          ▼
┌──────────────┐
│    CLOSED    │ (Normal operation, failures tracked)
└──────┬───────┘
       │ failures >= threshold
       │
       ▼
┌──────────────┐
│    OPEN      │ (Blocking requests)
└──────┬───────┘
       │ timeout elapsed
       │
       ▼
┌──────────────────┐
│   HALF_OPEN      │ (Testing recovery)
└──────┬───────────┘
       │
       ├─ success count >= threshold ──→ CLOSED
       │
       └─ any failure ──→ OPEN
```

### Usage Example

```python
from src.resilience import CircuitBreaker

# Create circuit breaker for PTZ control
ptz_breaker = CircuitBreaker(
    failure_threshold=5,      # Open after 5 failures
    timeout=30.0,             # Wait 30s before attempting recovery
    success_threshold=2,      # Require 2 successes to close
    name="ptz_controller"
)

# Use with decorator
@ptz_breaker
def pan_camera(angle):
    ptz_controller.pan(angle)

# Or manual usage
try:
    ptz_breaker.call(ptz_controller.pan, 45)
except CircuitBreakerOpen:
    logger.error("PTZ circuit is open, retrying later")

# Check status
status = ptz_breaker.get_status()
print(f"PTZ Breaker: {status['state']}, Failures: {status['failure_count']}")
```

### Metrics

- `state`: Current state (CLOSED, OPEN, HALF_OPEN)
- `failure_count`: Failures since last successful call
- `total_failures`: Total failures recorded
- `total_rejections`: Calls rejected while OPEN
- `elapsed_since_open`: Time since circuit opened

## Retry Policy

### Purpose
Recovers from transient failures using exponential backoff and jitter.

### Algorithm

```
Delay = base_delay * (multiplier ^ attempt)
Delay = min(Delay, max_delay)
Delay = random(0, Delay) if jitter enabled

Example with base=1s, multiplier=2:
Attempt 1: ~0.5s
Attempt 2: ~1.5s
Attempt 3: ~3.5s
Attempt 4: ~6s
```

### Usage Example

```python
from src.resilience import RetryPolicy

# Create retry policy
detection_retry = RetryPolicy(
    max_attempts=3,        # Try up to 3 times
    base_delay=0.5,        # Start with 0.5s delay
    max_delay=5.0,         # Cap at 5s delay
    jitter=True,           # Add randomness
    name="object_detection"
)

# Use with function
result = detection_retry(detector.detect, frame)

# Use with decorator
@detection_retry.decorator
def detect_objects(frame):
    return detector.detect(frame)

# Use with async functions
result = await detection_retry.call_async(async_detect, frame)

# Check metrics
metrics = detection_retry.get_metrics()
print(f"Success rate: {metrics['success_rate']}")
```

### Metrics

- `total_attempts`: Total function calls
- `total_successes`: Successful calls
- `total_failures`: Failed calls
- `retries_exhausted`: Times all retries failed
- `success_rate`: Percentage of successful operations
- `total_wait_time`: Total time spent in backoff delays

## Health Monitor

### Purpose
Tracks system health through regular health checks and generates alerts on failures.

### Health Status Levels

- **HEALTHY**: All components operating normally
- **DEGRADED**: Some components experiencing reduced performance
- **UNHEALTHY**: Critical failures detected
- **UNKNOWN**: No health checks have run

### Usage Example

```python
from src.resilience import HealthMonitor, HealthStatus

monitor = HealthMonitor(timeout=5.0)

# Register health checks
async def check_ptz():
    try:
        ptz_controller.get_status()
        return HealthStatus.HEALTHY
    except Exception:
        return HealthStatus.UNHEALTHY

monitor.register_check("ptz", check_ptz, "PTZ controller health")

# Run all checks
report = await monitor.run_checks()

# Check overall status
if report.overall == HealthStatus.UNHEALTHY:
    logger.critical("System health critical!")
    for alert in report.alerts:
        logger.error(alert)

# Get last report without running new checks
report = monitor.get_last_report()

# Get history
history = monitor.get_check_history("ptz", limit=10)
```

### Report Structure

```python
{
    "overall": "unhealthy",           # Aggregated status
    "timestamp": "2024-01-15T10:30:00",
    "checks": [
        {
            "name": "ptz_controller",
            "status": "healthy",
            "message": "PTZ controller health",
            "duration": "0.045s",
            "timestamp": "2024-01-15T10:30:00"
        },
        ...
    ],
    "alerts": [
        "SYSTEM HEALTH CRITICAL: One or more checks failed",
        "CRITICAL: detector is unhealthy: Model loading failed"
    ]
}
```

## Metrics Collection

### Purpose
Collects and analyzes system performance metrics with statistical analysis.

### Features

- **Latency Tracking**: Records operation durations with percentile calculations
- **Counters**: Tracks event counts
- **Thread-Safe**: Safe for concurrent access
- **Memory Management**: Limits sample storage

### Usage Example

```python
from src.monitoring import MetricsCollector

metrics = MetricsCollector()

# Record latencies with context manager
with metrics.timer("detection_latency"):
    detections = detector.detect(frame)

# Record counters
metrics.increment("frames_processed")
metrics.increment("ptz_movements", amount=1)

# Get statistics
stats = metrics.get_stats()
print(f"Detection p99: {stats['latencies']['detection_latency']['p99']}")

# Get summary
summary = metrics.get_summary()
print(f"Total events: {summary['total_events']}")
```

### Metrics Structure

```python
{
    "timestamp": "2024-01-15T10:30:00",
    "uptime": "3600.5s",
    "latencies": {
        "detection_latency": {
            "count": 1500,
            "min": "0.0123s",
            "max": "0.4567s",
            "mean": "0.1234s",
            "median": "0.1200s",
            "p50": "0.1200s",
            "p95": "0.2100s",
            "p99": "0.3400s"
        }
    },
    "counters": {
        "frames_processed": {"value": 1500},
        "detections": {"value": 450}
    }
}
```

## Integration with Tracking Engine

The resilience layer is integrated into the TrackingEngine automatically:

```python
# Circuit breaker for PTZ commands
self.ptz_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=30.0,
    name="ptz_controller"
)

# Retry policy for detection
self.detection_retry = RetryPolicy(
    max_attempts=3,
    base_delay=0.5,
    name="object_detection"
)

# Health monitor with automatic checks
self.health_monitor = HealthMonitor()
self.health_monitor.register_check("ptz_controller", self._health_check_ptz)
self.health_monitor.register_check("detector", self._health_check_detector)
self.health_monitor.register_check("video_stream", self._health_check_stream)

# Metrics collection for performance tracking
self.metrics = MetricsCollector(name="tracking_engine")
```

## Web API Endpoints

### `/api/health` - Simple Health Check

```
GET /api/health
Response:
{
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:00"
}
```

### `/api/health` (Detailed) - Comprehensive Health Report

```
GET /api/health
Response:
{
    "overall": "healthy",
    "timestamp": "2024-01-15T10:30:00",
    "checks": [
        {
            "name": "ptz_controller",
            "status": "healthy",
            "message": "PTZ camera controller connectivity",
            "duration": "0.045s",
            "timestamp": "2024-01-15T10:30:00"
        }
    ],
    "alerts": []
}
```

### `/api/metrics` - Performance Metrics

```
GET /api/metrics
Response:
{
    "timestamp": "2024-01-15T10:30:00",
    "uptime": "3600.5s",
    "latencies": {
        "detection_latency": {
            "count": 1500,
            "p99": "0.3400s",
            ...
        }
    },
    "tracking": {
        "frames_processed": 15000,
        "detections": 4500,
        "ptz_movements": 150,
        "active_events": 5,
        "completed_events": 250
    }
}
```

### `/api/resilience/status` - Resilience Layer Status

```
GET /api/resilience/status
Response:
{
    "timestamp": "2024-01-15T10:30:00",
    "circuit_breaker": {
        "ptz_controller": {
            "name": "ptz_controller",
            "state": "closed",
            "failure_count": 0,
            "total_rejections": 0,
            "failure_threshold": 5,
            "timeout": 30.0
        }
    },
    "retry_policies": {
        "object_detection": {
            "name": "object_detection",
            "total_attempts": 1500,
            "total_successes": 1492,
            "success_rate": "99.5%"
        }
    },
    "health": {
        "overall": "healthy",
        "checks": [...],
        "alerts": []
    }
}
```

## Best Practices

### Circuit Breaker
1. Use failure_threshold = 5 for most services (balance between responsiveness and false positives)
2. Use timeout = 30s to balance recovery time with availability
3. Monitor circuit_breaker.get_status() to understand failure patterns
4. Combine with retry policy for layered resilience

### Retry Policy
1. Use base_delay = 0.5-1.0s for most operations
2. Always enable jitter to prevent thundering herd
3. Cap max_delay at 5-10x base_delay
4. Use max_attempts = 3 for transient failures, 1 for permanent failures

### Health Monitor
1. Keep timeout = 5.0s or less to avoid blocking
2. Register checks for all critical components
3. Check health reports every 10-30 seconds
4. Set alert_on_degraded = False to reduce alert noise

### Metrics
1. Use timer() context manager for automatic latency tracking
2. Call get_summary() to see overview without full details
3. Review p95 and p99 percentiles for SLA compliance
4. Reset metrics daily or weekly to prevent unbounded memory

## Troubleshooting

### Circuit Breaker Opens Frequently
**Symptom**: Circuit frequently transitions to OPEN state

**Solutions**:
- Increase `failure_threshold` if failures are temporary
- Increase `timeout` if service takes longer to recover
- Check underlying service health with `/api/health`

### Retry Policy Exhausting Attempts
**Symptom**: "MaxRetriesExceeded" errors in logs

**Solutions**:
- Increase `max_attempts` if failures are temporary
- Increase `base_delay` if service needs more time
- Check underlying service with `/api/health`

### Health Checks Timing Out
**Symptom**: Health checks frequently fail with timeout

**Solutions**:
- Increase `HealthMonitor(timeout=...)` if checks are slow
- Optimize check implementations to run faster
- Check system resources (CPU, memory, network)

### Metrics Memory Growing
**Symptom**: Application memory usage increases over time

**Solutions**:
- Lower `max_samples` in MetricsCollector
- Call `metrics.reset()` periodically (daily)
- Check for metrics with high sample counts

## Production Deployment Checklist

- [ ] All health checks implemented and tested
- [ ] Circuit breaker timeouts tuned for your environment
- [ ] Retry policies configured for each operation type
- [ ] Metrics collection enabled
- [ ] Web endpoints accessible for monitoring
- [ ] Alerts configured for UNHEALTHY status
- [ ] Load testing performed to verify resilience
- [ ] Documentation shared with operations team
- [ ] Health check metrics reviewed regularly
- [ ] Incident response playbooks created
