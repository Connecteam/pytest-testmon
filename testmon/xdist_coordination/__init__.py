"""
pytest-testmon xdist support module.

This module provides coordination between xdist controller and worker processes
to enable proper readonly database access for parallel test execution.
"""

from .config import XdistConfig, get_xdist_config
from .coordination import CoordinationManager, CoordinationState
from .controller import (
    ControllerPreCreation,
    ControllerState,
    get_controller_state,
    reset_controller_state,
)
from .worker import (
    WorkerCoordination,
    WorkerState,
    initialize_worker,
)
from .exceptions import (
    CoordinationError,
    CoordinationTimeout,
    WorkerNotReady,
    ControllerNotReady,
    CoordinationFileError,
    InvalidCoordinationState,
)

__all__ = [
    # Config
    "XdistConfig",
    "get_xdist_config",
    # Coordination
    "CoordinationManager",
    "CoordinationState",
    # Controller
    "ControllerPreCreation",
    "ControllerState",
    "get_controller_state",
    "reset_controller_state",
    # Worker
    "WorkerCoordination",
    "WorkerState",
    "initialize_worker",
    # Exceptions
    "CoordinationError",
    "CoordinationTimeout",
    "WorkerNotReady",
    "ControllerNotReady",
    "CoordinationFileError",
    "InvalidCoordinationState",
]

__version__ = "0.1.0"
