"""
Controller-side logic for xdist coordination.

This module handles database pre-creation and preparation for worker processes.
"""

import os
from typing import Dict, Any, List, Optional, Set
from pathlib import Path

from testmon.common import get_logger
from testmon.db import DB
from testmon.testmon_core import TestmonData, get_data_file_path
from .config import get_xdist_config
from .coordination import CoordinationManager, CoordinationState
from .exceptions import ControllerNotReady, CoordinationError

logger = get_logger(__name__)


class ControllerPreCreation:
    """Handles database pre-creation for xdist controller process."""

    def __init__(self, testmon_data: TestmonData):
        """
        Initialize controller pre-creation handler.

        Args:
            testmon_data: The TestmonData instance to work with
        """
        self.testmon_data = testmon_data
        self.config = get_xdist_config()
        self.coordination_manager = CoordinationManager(testmon_data.rootdir)
        self._precreated_data: Dict[str, Any] = {}

    def prepare_for_workers(
        self, num_workers: Optional[int] = None
    ) -> CoordinationState:
        """
        Prepare database for worker processes.

        This is the main entry point for controller pre-creation.

        Args:
            num_workers: Expected number of workers (optional)

        Returns:
            CoordinationState that was written for workers

        Raises:
            ControllerNotReady: If preparation fails
        """
        try:
            logger.info(
                f"Controller preparing database for {num_workers or 'unknown'} workers"
            )

            # 1. Pre-create environment
            env_data = self._precreate_environment()

            # 2. Scan and pre-register test files
            test_files = self._scan_test_files()

            # 3. Pre-populate any known data
            known_data = self._prepopulate_known_data(test_files)

            # 4. Create coordination state
            database_path = os.path.join(
                self.testmon_data.rootdir, get_data_file_path()
            )
            state_data = {
                "environment_id": env_data["environment_id"],
                "database_path": database_path,
                "expected_workers": num_workers,
                "precreated_entries": {
                    "environment": env_data,
                    "test_files": test_files,
                    "known_data": known_data,
                },
            }

            # 5. Write state for workers
            state = self.coordination_manager.write_controller_state(state_data)

            logger.info(
                f"Controller prepared database with environment_id={env_data['environment_id']}"
            )

            # 6. Wait for workers if count is known
            if num_workers:
                success = self.coordination_manager.wait_for_workers(
                    expected_count=num_workers,
                    timeout=10,  # Reasonable timeout for workers to start
                )
                if not success:
                    logger.warning("Not all workers acknowledged in time")

            return state

        except Exception as e:
            logger.error(f"Controller preparation failed: {e}")
            raise ControllerNotReady(f"Failed to prepare database: {e}")

    def _precreate_environment(self) -> Dict[str, Any]:
        """
        Pre-create the environment entry in database.

        Returns:
            Dictionary with environment data
        """
        # Get environment data from testmon_data
        environment_name = self.testmon_data.environment
        system_packages = getattr(self.testmon_data, "system_packages", "")
        python_version = getattr(self.testmon_data, "python_version", "")

        # Use the database's initiate_execution to create environment
        result = self.testmon_data.db.initiate_execution(
            environment_name,
            system_packages,
            python_version,
            {"controller_precreate": True},
        )

        env_data = {
            "environment_id": result["exec_id"],
            "environment_name": environment_name,
            "system_packages": system_packages,
            "python_version": python_version,
            "packages_changed": result.get("packages_changed", False),
        }

        logger.debug(f"Pre-created environment: {env_data}")

        return env_data

    def _scan_test_files(self) -> List[str]:
        """
        Scan for test files in the project.

        Returns:
            List of test file paths relative to rootdir
        """
        test_files = []
        rootdir = Path(self.testmon_data.rootdir)

        # Common test directory patterns
        test_patterns = [
            "test_*.py",
            "*_test.py",
            "tests.py",
        ]

        # Common test directories
        test_dirs = [
            "tests",
            "test",
            "testing",
            "tests/unit",
            "tests/integration",
            "test/unit",
            "test/integration",
        ]

        # Also check root directory
        test_dirs.append(".")

        for test_dir_name in test_dirs:
            test_dir = rootdir / test_dir_name
            if not test_dir.exists():
                continue

            # Find test files
            for pattern in test_patterns:
                for test_file in test_dir.rglob(pattern):
                    if test_file.is_file():
                        # Get relative path
                        try:
                            rel_path = test_file.relative_to(rootdir)
                            test_files.append(str(rel_path))
                        except ValueError:
                            # File is outside rootdir, skip
                            pass

        # Remove duplicates and sort
        test_files = sorted(list(set(test_files)))

        logger.debug(f"Found {len(test_files)} test files")

        return test_files

    def _prepopulate_known_data(self, test_files: List[str]) -> Dict[str, Any]:
        """
        Pre-populate any known data that workers might need.

        Args:
            test_files: List of test files found

        Returns:
            Dictionary of pre-populated data
        """
        known_data = {
            "test_file_count": len(test_files),
            "rootdir": self.testmon_data.rootdir,
        }

        # Pre-register test files in the database if needed
        # This helps avoid concurrent writes from workers
        if hasattr(self.testmon_data.db, "register_test_files"):
            try:
                self.testmon_data.db.register_test_files(test_files)
                known_data["test_files_registered"] = True
            except AttributeError:
                # Method doesn't exist, that's ok
                known_data["test_files_registered"] = False

        return known_data

    def cleanup(self):
        """Clean up coordination files after test run."""
        try:
            self.coordination_manager.cleanup()
        except Exception as e:
            logger.warning(f"Failed to cleanup coordination files: {e}")


class ControllerState:
    """Manages controller state during test execution."""

    def __init__(self):
        """Initialize controller state."""
        self.is_initialized = False
        self.environment_id: Optional[int] = None
        self.num_workers: Optional[int] = None
        self.precreation_handler: Optional[ControllerPreCreation] = None

    def initialize(self, testmon_data: TestmonData, num_workers: Optional[int] = None):
        """
        Initialize controller state.

        Args:
            testmon_data: TestmonData instance
            num_workers: Expected number of workers
        """
        if self.is_initialized:
            logger.debug("Controller state already initialized")
            return

        self.precreation_handler = ControllerPreCreation(testmon_data)
        self.num_workers = num_workers

        # Perform pre-creation
        state = self.precreation_handler.prepare_for_workers(num_workers)
        self.environment_id = state.environment_id

        self.is_initialized = True

    def cleanup(self):
        """Clean up controller state."""
        if self.precreation_handler:
            self.precreation_handler.cleanup()

        self.is_initialized = False
        self.environment_id = None
        self.num_workers = None
        self.precreation_handler = None


# Global controller state instance
_controller_state: Optional[ControllerState] = None


def get_controller_state() -> ControllerState:
    """Get the global controller state instance."""
    global _controller_state
    if _controller_state is None:
        _controller_state = ControllerState()
    return _controller_state


def reset_controller_state():
    """Reset the global controller state (mainly for testing)."""
    global _controller_state
    if _controller_state:
        _controller_state.cleanup()
    _controller_state = None
