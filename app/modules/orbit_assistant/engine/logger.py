"""
Shared structured logger for Orbit Governance Assistant.
Provides debug-level observability across all modules.
"""

import logging
import sys
from datetime import datetime, timezone


class OrbitFormatter(logging.Formatter):
    """Custom formatter: [LEVEL] module | message"""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        module = record.name.ljust(22)
        return (
            f"{color}[{record.levelname:<7}]{self.RESET} "
            f"{timestamp} {module} | {record.getMessage()}"
        )


def get_logger(module_name: str) -> logging.Logger:
    """Get a structured logger for a given module."""
    logger = logging.getLogger(f"orbit.{module_name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(OrbitFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
    return logger
