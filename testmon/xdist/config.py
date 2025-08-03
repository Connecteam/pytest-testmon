"""
Configuration for xdist support in testmon.

This module handles feature flags, configuration options, and settings
for the controller pre-creation functionality.
"""

import os
from typing import Optional, Dict, Any
from testmon.common import get_logger

logger = get_logger(__name__)


class XdistConfig:
    """Configuration for xdist coordination features."""

    # Feature flags
    ENABLE_CONTROLLER_PRECREATION = "TESTMON_XDIST_CONTROLLER_PRECREATION"
    ENABLE_COORDINATION_DEBUG = "TESTMON_XDIST_DEBUG"

    # Timing configurations
    DEFAULT_WORKER_TIMEOUT = 30  # seconds
    DEFAULT_COORDINATION_CHECK_INTERVAL = 0.1  # seconds
    DEFAULT_COORDINATION_BACKOFF_FACTOR = 1.5
    DEFAULT_COORDINATION_MAX_INTERVAL = 2.0  # seconds

    # File paths
    COORDINATION_DIR_NAME = ".testmon_xdist"
    READY_MARKER_NAME = "controller_ready.json"
    WORKER_ACK_PATTERN = "worker_{}_ready"

    def __init__(self):
        """Initialize configuration from environment and defaults."""
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {
            "enabled": self._get_bool_env(
                self.ENABLE_CONTROLLER_PRECREATION, default=False
            ),
            "debug": self._get_bool_env(self.ENABLE_COORDINATION_DEBUG, default=False),
            "worker_timeout": self._get_int_env(
                "TESTMON_XDIST_WORKER_TIMEOUT", default=self.DEFAULT_WORKER_TIMEOUT
            ),
            "check_interval": self._get_float_env(
                "TESTMON_XDIST_CHECK_INTERVAL",
                default=self.DEFAULT_COORDINATION_CHECK_INTERVAL,
            ),
            "backoff_factor": self._get_float_env(
                "TESTMON_XDIST_BACKOFF_FACTOR",
                default=self.DEFAULT_COORDINATION_BACKOFF_FACTOR,
            ),
            "max_interval": self._get_float_env(
                "TESTMON_XDIST_MAX_INTERVAL",
                default=self.DEFAULT_COORDINATION_MAX_INTERVAL,
            ),
        }

        if config["debug"]:
            logger.info(f"XdistConfig loaded: {config}")

        return config

    @staticmethod
    def _get_bool_env(key: str, default: bool = False) -> bool:
        """Get boolean value from environment variable."""
        value = os.environ.get(key, "").lower()
        if value in ("1", "true", "yes", "on"):
            return True
        elif value in ("0", "false", "no", "off"):
            return False
        return default

    @staticmethod
    def _get_int_env(key: str, default: int) -> int:
        """Get integer value from environment variable."""
        try:
            return int(os.environ.get(key, default))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _get_float_env(key: str, default: float) -> float:
        """Get float value from environment variable."""
        try:
            return float(os.environ.get(key, default))
        except (ValueError, TypeError):
            return default

    @property
    def enabled(self) -> bool:
        """Check if controller pre-creation is enabled."""
        return self._config["enabled"]

    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self._config["debug"]

    @property
    def worker_timeout(self) -> int:
        """Get worker timeout in seconds."""
        return self._config["worker_timeout"]

    @property
    def check_interval(self) -> float:
        """Get initial check interval for coordination."""
        return self._config["check_interval"]

    @property
    def backoff_factor(self) -> float:
        """Get backoff factor for coordination retries."""
        return self._config["backoff_factor"]

    @property
    def max_interval(self) -> float:
        """Get maximum check interval for coordination."""
        return self._config["max_interval"]

    def get_coordination_dir(self, rootdir: str) -> str:
        """Get the coordination directory path."""
        return os.path.join(rootdir, self.COORDINATION_DIR_NAME)

    def get_ready_marker_path(self, rootdir: str) -> str:
        """Get the ready marker file path."""
        return os.path.join(self.get_coordination_dir(rootdir), self.READY_MARKER_NAME)

    def get_worker_ack_path(self, rootdir: str, worker_id: str) -> str:
        """Get the worker acknowledgment file path."""
        filename = self.WORKER_ACK_PATTERN.format(worker_id)
        return os.path.join(self.get_coordination_dir(rootdir), filename)

    def validate(self) -> bool:
        """Validate the configuration."""
        if self.worker_timeout <= 0:
            logger.error(f"Invalid worker_timeout: {self.worker_timeout}")
            return False

        if self.check_interval <= 0:
            logger.error(f"Invalid check_interval: {self.check_interval}")
            return False

        if self.backoff_factor <= 1.0:
            logger.error(f"Invalid backoff_factor: {self.backoff_factor}")
            return False

        return True


# Global configuration instance
_config: Optional[XdistConfig] = None


def get_xdist_config() -> XdistConfig:
    """Get the global xdist configuration instance."""
    global _config
    if _config is None:
        _config = XdistConfig()
    return _config


def reset_config():
    """Reset the global configuration (mainly for testing)."""
    global _config
    _config = None
