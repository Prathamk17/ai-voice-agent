"""
Structured logging utility with support for development and production environments.
"""

import logging
import sys
from typing import Optional
import json
from datetime import datetime


class StructuredLogger:
    """
    Structured logger with request ID tracking and environment-specific formatting.

    In development: Human-readable logs
    In production: JSON-formatted logs for log aggregation systems
    """

    def __init__(self, name: str, environment: str = "development"):
        """
        Initialize logger.

        Args:
            name: Logger name (typically __name__ of the module)
            environment: Environment (development/staging/production)
        """
        self.logger = logging.getLogger(name)
        self.environment = environment
        self._setup_logger()

    def _setup_logger(self):
        """Configure logger based on environment"""
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Create handler
        handler = logging.StreamHandler(sys.stdout)

        # Use JSON formatter in production, simple formatter in dev
        if self.environment == "production":
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )

        self.logger.addHandler(handler)
        self.logger.propagate = False  # Prevent duplicate logs

    def info(self, message: str, **kwargs):
        """Log info level message"""
        self.logger.info(self._format_message(message, kwargs))

    def error(self, message: str, **kwargs):
        """Log error level message"""
        self.logger.error(self._format_message(message, kwargs))

    def warning(self, message: str, **kwargs):
        """Log warning level message"""
        self.logger.warning(self._format_message(message, kwargs))

    def debug(self, message: str, **kwargs):
        """Log debug level message"""
        self.logger.debug(self._format_message(message, kwargs))

    def critical(self, message: str, **kwargs):
        """Log critical level message"""
        self.logger.critical(self._format_message(message, kwargs))

    def _format_message(self, message: str, extra: dict) -> str:
        """
        Format message based on environment.

        In production: Return JSON string
        In development: Return human-readable string with extras
        """
        if self.environment == "production":
            return json.dumps({
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                **extra
            })

        # Development: human-readable format
        if extra:
            extra_str = " | " + ", ".join([f"{k}={v}" for k, v in extra.items()])
            return f"{message}{extra_str}"
        return message


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging in production.
    Outputs logs in JSON format suitable for log aggregation systems.
    """

    def format(self, record):
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add call_sid if available (for tracking specific calls)
        if hasattr(record, 'call_sid'):
            log_data['call_sid'] = record.call_sid

        # Add request_id if available (for tracking HTTP requests)
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


# Convenience function to get logger
def get_logger(name: str, environment: str = "development") -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)
        environment: Environment (development/staging/production)

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name, environment)
