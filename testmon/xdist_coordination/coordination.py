"""
Coordination primitives for controller-worker communication.

This module provides file-based coordination between xdist controller
and worker processes.
"""

import json
import os
import shutil
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from contextlib import contextmanager

from testmon.common import get_logger
from .config import get_xdist_config
from .exceptions import (
    CoordinationError,
    CoordinationTimeout,
    CoordinationFileError,
    InvalidCoordinationState,
)

logger = get_logger(__name__)


class CoordinationState:
    """Container for coordination state data."""
    
    def __init__(self, data: Dict[str, Any]):
        self.timestamp = data.get("timestamp", 0)
        self.controller_pid = data.get("controller_pid")
        self.environment_id = data.get("environment_id")
        self.database_path = data.get("database_path")
        self.expected_workers = data.get("expected_workers")
        self.precreated_entries = data.get("precreated_entries", {})
        self._raw_data = data
        
    def is_valid(self, max_age: float = 300) -> bool:
        """Check if the state is valid and recent."""
        if not self.timestamp or not self.controller_pid:
            return False
            
        age = time.time() - self.timestamp
        return age < max_age
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert back to dictionary."""
        return self._raw_data.copy()


class CoordinationManager:
    """Manages coordination between controller and worker processes."""
    
    def __init__(self, rootdir: str):
        self.rootdir = rootdir
        self.config = get_xdist_config()
        self.coordination_dir = self.config.get_coordination_dir(rootdir)
        self._ensure_coordination_dir()
        
    def _ensure_coordination_dir(self):
        """Create coordination directory if it doesn't exist."""
        try:
            os.makedirs(self.coordination_dir, exist_ok=True)
        except OSError as e:
            raise CoordinationFileError(
                self.coordination_dir, "create directory", e
            )
    
    @contextmanager
    def _atomic_write(self, filepath: str):
        """Context manager for atomic file writes."""
        temp_path = f"{filepath}.tmp"
        try:
            yield temp_path
            # Atomic rename on POSIX systems
            os.replace(temp_path, filepath)
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            raise CoordinationFileError(filepath, "write", e)
    
    def write_controller_state(self, state_data: Dict[str, Any]) -> CoordinationState:
        """Write controller state for workers to read."""
        state_data["timestamp"] = time.time()
        state_data["controller_pid"] = os.getpid()
        
        state = CoordinationState(state_data)
        marker_path = self.config.get_ready_marker_path(self.rootdir)
        
        if self.config.debug:
            logger.debug(f"Writing controller state to {marker_path}")
        
        with self._atomic_write(marker_path) as temp_path:
            with open(temp_path, 'w') as f:
                json.dump(state.to_dict(), f, indent=2)
        
        return state
    
    def read_controller_state(self) -> Optional[CoordinationState]:
        """Read controller state if available."""
        marker_path = self.config.get_ready_marker_path(self.rootdir)
        
        if not os.path.exists(marker_path):
            return None
            
        try:
            with open(marker_path, 'r') as f:
                data = json.load(f)
            state = CoordinationState(data)
            
            if not state.is_valid():
                logger.warning(f"Found stale controller state (age: {time.time() - state.timestamp}s)")
                return None
                
            return state
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise InvalidCoordinationState("controller state", str(e))
    
    def wait_for_controller(self, worker_id: str, timeout: Optional[float] = None) -> CoordinationState:
        """
        Wait for controller to signal readiness.
        
        Args:
            worker_id: Unique worker identifier
            timeout: Maximum time to wait (uses config default if None)
            
        Returns:
            CoordinationState from controller
            
        Raises:
            CoordinationTimeout: If controller doesn't signal in time
        """
        timeout = timeout or self.config.worker_timeout
        start_time = time.time()
        check_interval = self.config.check_interval
        
        logger.info(f"Worker {worker_id} waiting for controller (timeout: {timeout}s)")
        
        while time.time() - start_time < timeout:
            state = self.read_controller_state()
            if state and state.is_valid():
                logger.info(f"Worker {worker_id} received controller state")
                self.acknowledge_worker_ready(worker_id)
                return state
                
            time.sleep(check_interval)
            # Exponential backoff
            check_interval = min(
                check_interval * self.config.backoff_factor,
                self.config.max_interval
            )
        
        raise CoordinationTimeout("wait_for_controller", timeout)
    
    def acknowledge_worker_ready(self, worker_id: str):
        """Signal that a worker is ready."""
        ack_path = self.config.get_worker_ack_path(self.rootdir, worker_id)
        
        if self.config.debug:
            logger.debug(f"Worker {worker_id} acknowledging ready at {ack_path}")
            
        try:
            Path(ack_path).touch()
        except OSError as e:
            raise CoordinationFileError(ack_path, "acknowledge", e)
    
    def get_ready_workers(self) -> Set[str]:
        """Get set of workers that have acknowledged readiness."""
        ready_workers = set()
        
        try:
            pattern = self.config.WORKER_ACK_PATTERN.format("*")
            for ack_file in Path(self.coordination_dir).glob(pattern):
                # Extract worker ID from filename
                worker_id = ack_file.stem.replace("worker_", "").replace("_ready", "")
                ready_workers.add(worker_id)
                
        except OSError as e:
            logger.warning(f"Error scanning for ready workers: {e}")
            
        return ready_workers
    
    def wait_for_workers(self, expected_count: int, timeout: float = 10) -> bool:
        """
        Wait for expected number of workers to acknowledge readiness.
        
        Args:
            expected_count: Number of workers to wait for
            timeout: Maximum time to wait
            
        Returns:
            True if all workers ready, False if timeout
        """
        start_time = time.time()
        check_interval = self.config.check_interval
        
        logger.info(f"Controller waiting for {expected_count} workers")
        
        while time.time() - start_time < timeout:
            ready_workers = self.get_ready_workers()
            ready_count = len(ready_workers)
            
            if ready_count >= expected_count:
                logger.info(f"All {ready_count} workers ready")
                return True
                
            if self.config.debug:
                logger.debug(f"Workers ready: {ready_count}/{expected_count}")
                
            time.sleep(check_interval)
            check_interval = min(
                check_interval * self.config.backoff_factor,
                self.config.max_interval
            )
        
        ready_workers = self.get_ready_workers()
        logger.warning(
            f"Worker timeout: {len(ready_workers)}/{expected_count} ready after {timeout}s"
        )
        return False
    
    def cleanup(self):
        """Clean up coordination files."""
        if os.path.exists(self.coordination_dir):
            try:
                shutil.rmtree(self.coordination_dir)
                logger.info("Cleaned up coordination directory")
            except OSError as e:
                logger.warning(f"Failed to cleanup coordination directory: {e}")
    
    def reset_worker_acknowledgments(self):
        """Remove all worker acknowledgment files."""
        try:
            pattern = self.config.WORKER_ACK_PATTERN.format("*")
            for ack_file in Path(self.coordination_dir).glob(pattern):
                ack_file.unlink()
        except OSError as e:
            logger.warning(f"Failed to reset worker acknowledgments: {e}")