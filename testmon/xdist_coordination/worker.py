"""
Worker-side logic for xdist coordination.

This module handles worker synchronization and readonly database access.
"""

import os
import time
from typing import Optional, Dict, Any

from testmon.common import get_logger
from testmon.testmon_core import TestmonData
from .config import get_xdist_config
from .coordination import CoordinationManager, CoordinationState
from .exceptions import WorkerNotReady, CoordinationTimeout

logger = get_logger(__name__)


class WorkerCoordination:
    """Handles worker-side coordination with controller."""

    def __init__(self, worker_id: str, rootdir: str):
        """
        Initialize worker coordination handler.

        Args:
            worker_id: Unique worker identifier (e.g., "gw0", "gw1")
            rootdir: Project root directory
        """
        self.worker_id = worker_id
        self.rootdir = rootdir
        self.config = get_xdist_config()
        self.coordination_manager = CoordinationManager(rootdir)
        self.controller_state: Optional[CoordinationState] = None
        self._is_ready = False

    def wait_and_initialize(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Wait for controller signal and initialize worker.

        Args:
            timeout: Maximum time to wait (uses config default if None)

        Returns:
            Dictionary with initialization data from controller

        Raises:
            WorkerNotReady: If initialization fails
            CoordinationTimeout: If controller doesn't signal in time
        """
        try:
            logger.info(f"Worker {self.worker_id} waiting for controller signal")

            # Wait for controller state
            self.controller_state = self.coordination_manager.wait_for_controller(
                self.worker_id, timeout=timeout
            )

            # Extract initialization data
            init_data = {
                "worker_id": self.worker_id,
                "environment_id": self.controller_state.environment_id,
                "database_path": self.controller_state.database_path,
                "precreated_entries": self.controller_state.precreated_entries,
            }

            logger.info(
                f"Worker {self.worker_id} initialized with "
                f"environment_id={self.controller_state.environment_id}"
            )

            self._is_ready = True
            return init_data

        except CoordinationTimeout:
            logger.error(f"Worker {self.worker_id} timeout waiting for controller")
            raise
        except Exception as e:
            logger.error(f"Worker {self.worker_id} initialization failed: {e}")
            raise WorkerNotReady(self.worker_id, str(e))

    def get_environment_id(self) -> Optional[int]:
        """
        Get the environment ID from controller state.

        Returns:
            Environment ID or None if not initialized
        """
        if self.controller_state:
            return self.controller_state.environment_id
        return None

    def get_database_path(self) -> Optional[str]:
        """
        Get the database path from controller state.

        Returns:
            Database path or None if not initialized
        """
        if self.controller_state:
            return self.controller_state.database_path
        return None

    def is_ready(self) -> bool:
        """Check if worker is ready."""
        return self._is_ready

    def get_precreated_data(self, key: str) -> Any:
        """
        Get specific precreated data from controller.

        Args:
            key: Key to lookup in precreated_entries

        Returns:
            The value for the key, or None if not found
        """
        if self.controller_state and self.controller_state.precreated_entries:
            return self.controller_state.precreated_entries.get(key)
        return None


class WorkerState:
    """Manages worker state during test execution."""

    def __init__(self):
        """Initialize worker state."""
        self.is_initialized = False
        self.worker_id: Optional[str] = None
        self.coordination_handler: Optional[WorkerCoordination] = None
        self.environment_id: Optional[int] = None
        self.testmon_data: Optional[TestmonData] = None

    def initialize(self, worker_id: str, rootdir: str, timeout: Optional[float] = None):
        """
        Initialize worker state.

        Args:
            worker_id: Worker identifier
            rootdir: Project root directory
            timeout: Maximum time to wait for controller

        Raises:
            WorkerNotReady: If initialization fails
        """
        if self.is_initialized:
            logger.debug(f"Worker {worker_id} state already initialized")
            return

        self.worker_id = worker_id
        self.coordination_handler = WorkerCoordination(worker_id, rootdir)

        # Wait for controller and get initialization data
        init_data = self.coordination_handler.wait_and_initialize(timeout)
        self.environment_id = init_data["environment_id"]

        # Initialize TestmonData in readonly mode
        # This will be done by the calling code using the environment_id

        self.is_initialized = True

    def create_readonly_testmon_data(
        self, rootdir: str, environment: str, system_packages: str, python_version: str
    ) -> TestmonData:
        """
        Create a TestmonData instance in readonly mode.

        This uses the environment_id from controller to avoid
        trying to create a new environment.

        Args:
            rootdir: Project root directory
            environment: Environment name
            system_packages: System packages string
            python_version: Python version string

        Returns:
            TestmonData instance in readonly mode
        """
        if not self.is_initialized:
            raise WorkerNotReady(self.worker_id, "Worker not initialized")

        # Create TestmonData with readonly=True
        # The environment_id from controller ensures we don't
        # try to create a new environment
        testmon_data = TestmonData(
            rootdir=rootdir,
            environment=environment,
            system_packages=system_packages,
            python_version=python_version,
            readonly=True,
        )

        # Store reference
        self.testmon_data = testmon_data

        return testmon_data

    def cleanup(self):
        """Clean up worker state."""
        self.is_initialized = False
        self.worker_id = None
        self.coordination_handler = None
        self.environment_id = None
        self.testmon_data = None


def initialize_worker(worker_id: str, config) -> Optional[WorkerState]:
    """
    Initialize a worker with coordination.

    This is a convenience function for pytest hook integration.

    Args:
        worker_id: Worker identifier
        config: pytest config object

    Returns:
        WorkerState instance or None if not using coordination
    """
    xdist_config = get_xdist_config()

    if not xdist_config.enabled:
        logger.debug("Worker coordination disabled")
        return None

    try:
        rootdir = str(config.rootdir)
        worker_state = WorkerState()
        worker_state.initialize(worker_id, rootdir)

        logger.info(f"Worker {worker_id} initialized with coordination")
        return worker_state

    except Exception as e:
        logger.error(f"Failed to initialize worker {worker_id}: {e}")
        # Continue without coordination
        return None
