"""
Automation Module

Automated tracking logic and coordination of all system components.
"""

from .tracking_engine import (
    TrackingEngine,
    TrackingConfig,
    TrackingZone,
    TrackingMode,
    TrackingEvent
)

__all__ = [
    'TrackingEngine',
    'TrackingConfig',
    'TrackingZone',
    'TrackingMode',
    'TrackingEvent'
]
