"""
pytest-testmon xdist support module.

This module provides coordination between xdist controller and worker processes
to enable proper readonly database access for parallel test execution.
"""

from .config import XdistConfig
from .coordination import CoordinationManager
from .exceptions import (
    CoordinationError,
    CoordinationTimeout,
    WorkerNotReady,
)

__all__ = [
    "XdistConfig",
    "CoordinationManager",
    "CoordinationError",
    "CoordinationTimeout",
    "WorkerNotReady",
]

__version__ = "0.1.0"
