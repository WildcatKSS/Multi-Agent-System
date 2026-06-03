"""Structured logging configuration."""

import json
import logging
import sys
from typing import Any, Optional

from mas.observability.correlation import get_correlation_id


class StructuredLogFormatter(logging.Formatter):
    """Formats log records as JSON for structured logging.

    Includes correlation ID (run_id) in all log records for distributed tracing.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON.

        Args:
            record: Log record to format.

        Returns:
            JSON string containing structured log data.
        """
        log_data: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, self.datefmt),
        }

        # Add correlation ID (run_id) if available
        correlation_id = get_correlation_id()
        if correlation_id:
            log_data["run_id"] = correlation_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields passed via record attributes
        for key in record.__dict__:
            if key not in {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
            }:
                log_data[key] = getattr(record, key)

        return json.dumps(log_data)


def configure_logging(
    level: int = logging.INFO,
    format_json: bool = True,
    stream: Optional[Any] = None,
) -> None:
    """Configure structured logging for the application.

    Args:
        level: Logging level (default INFO).
        format_json: Whether to use JSON formatting (default True).
        stream: Output stream (default sys.stderr).
    """
    if stream is None:
        stream = sys.stderr

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(stream)
    console_handler.setLevel(level)

    # Set formatter
    if format_json:
        formatter = StructuredLogFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
