"""
Structured logging module for the attendance reporting system.
Provides enhanced logging with performance metrics, correlation IDs, and structured JSON output.
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from pathlib import Path
import sys


class LogLevel(Enum):
    """Log levels with corresponding numeric values."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class PerformanceTracker:
    """Context manager for tracking performance metrics."""

    def __init__(self, logger: 'StructuredLogger', operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"Starting {self.operation}", extra={
            'operation': self.operation,
            'phase': 'start',
            **self.context
        })
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time

        log_data = {
            'operation': self.operation,
            'phase': 'end',
            'duration_seconds': round(duration, 3),
            'duration_ms': round(duration * 1000, 1),
            **self.context
        }

        if exc_type is not None:
            log_data['error'] = str(exc_val)
            log_data['error_type'] = exc_type.__name__
            self.logger.error(f"Failed {self.operation}", extra=log_data)
        else:
            self.logger.info(f"Completed {self.operation}", extra=log_data)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add correlation ID if available
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id

        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info'
            }:
                log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """Colored formatter for console output during development."""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors for console."""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Basic format for console
        formatted = f"{color}[{record.levelname:8}]{reset} " \
                   f"{datetime.fromtimestamp(record.created).strftime('%H:%M:%S')} " \
                   f"{record.name}: {record.getMessage()}"

        # Add operation info if available
        if hasattr(record, 'operation'):
            formatted += f" | Operation: {record.operation}"

        # Add duration if available
        if hasattr(record, 'duration_ms'):
            formatted += f" | Duration: {record.duration_ms}ms"

        # Add correlation ID if available
        if hasattr(record, 'correlation_id'):
            formatted += f" | CID: {record.correlation_id[:8]}"

        return formatted


class StructuredLogger:
    """Enhanced logger with structured output and performance tracking."""

    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        log_file: Optional[str] = None,
        enable_console: bool = True,
        enable_json: bool = True,
        correlation_id: Optional[str] = None
    ):
        """
        Initialize structured logger.

        Args:
            name: Logger name
            level: Log level
            log_file: Optional log file path
            enable_console: Enable console output
            enable_json: Enable JSON structured output
            correlation_id: Optional correlation ID for request tracking
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level.value)

        # Clear existing handlers
        self.logger.handlers.clear()

        # Set correlation ID
        self.correlation_id = correlation_id or str(uuid.uuid4())[:8]

        # Add console handler
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level.value)
            console_handler.setFormatter(ColoredConsoleFormatter())
            self.logger.addHandler(console_handler)

        # Add file handler with JSON formatting
        if log_file or enable_json:
            log_path = log_file or "logs/attendance_system.log"
            log_path = Path(log_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setLevel(level.value)
            file_handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(file_handler)

        # Prevent propagation to root logger
        self.logger.propagate = False

    def _log_with_context(self, level: LogLevel, message: str, **kwargs):
        """Log message with additional context."""
        extra = kwargs.get('extra', {})
        extra['correlation_id'] = self.correlation_id
        kwargs['extra'] = extra
        self.logger.log(level.value, message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log_with_context(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log_with_context(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log_with_context(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log_with_context(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log_with_context(LogLevel.CRITICAL, message, **kwargs)

    def performance(self, operation: str, **context):
        """
        Create a performance tracker context manager.

        Args:
            operation: Name of the operation being tracked
            **context: Additional context information

        Returns:
            PerformanceTracker context manager
        """
        return PerformanceTracker(self, operation, **context)

    def log_metric(self, metric_name: str, value: float, unit: str = None, **context):
        """
        Log a performance metric.

        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Optional unit (e.g., 'ms', 'count', 'MB')
            **context: Additional context
        """
        extra = {
            'metric_name': metric_name,
            'metric_value': value,
            'metric_unit': unit,
            **context
        }
        self.info(f"Metric: {metric_name}={value}{f' {unit}' if unit else ''}", extra=extra)

    def log_api_request(self, method: str, url: str, status_code: int, duration_ms: float, **context):
        """
        Log API request details.

        Args:
            method: HTTP method
            url: Request URL
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
            **context: Additional context
        """
        extra = {
            'api_method': method,
            'api_url': url,
            'api_status_code': status_code,
            'api_duration_ms': duration_ms,
            **context
        }

        if status_code >= 400:
            self.error(f"API Request Failed: {method} {url} -> {status_code}", extra=extra)
        else:
            self.info(f"API Request: {method} {url} -> {status_code}", extra=extra)

    def log_database_query(self, query_type: str, table: str, duration_ms: float, rows_affected: int = None, **context):
        """
        Log database query details.

        Args:
            query_type: Type of query (SELECT, INSERT, UPDATE, etc.)
            table: Table name
            duration_ms: Query duration in milliseconds
            rows_affected: Number of rows affected
            **context: Additional context
        """
        extra = {
            'db_query_type': query_type,
            'db_table': table,
            'db_duration_ms': duration_ms,
            'db_rows_affected': rows_affected,
            **context
        }

        self.info(f"DB Query: {query_type} {table} ({duration_ms}ms)", extra=extra)

    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for request tracking."""
        self.correlation_id = correlation_id

    def get_correlation_id(self) -> str:
        """Get current correlation ID."""
        return self.correlation_id


# Global logger instances
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(
    name: str,
    level: LogLevel = LogLevel.INFO,
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_json: bool = True
) -> StructuredLogger:
    """
    Get or create a structured logger instance.

    Args:
        name: Logger name
        level: Log level
        log_file: Optional log file path
        enable_console: Enable console output
        enable_json: Enable JSON structured output

    Returns:
        StructuredLogger instance
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(
            name=name,
            level=level,
            log_file=log_file,
            enable_console=enable_console,
            enable_json=enable_json
        )
    return _loggers[name]


def configure_logging(
    level: LogLevel = LogLevel.INFO,
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_json: bool = True
):
    """
    Configure logging for the entire application.

    Args:
        level: Default log level
        log_file: Default log file path
        enable_console: Enable console output for default loggers
        enable_json: Enable JSON structured output for default loggers
    """
    # Create default loggers for key modules
    modules = [
        'data_processor',
        'api_client',
        'db_postgres_connection',
        'report_generator',
        'main'
    ]

    for module in modules:
        get_logger(
            name=module,
            level=level,
            log_file=log_file,
            enable_console=enable_console,
            enable_json=enable_json
        )


# Performance decorator for automatic function timing
def log_performance(operation_name: Optional[str] = None, logger_name: str = 'default'):
    """
    Decorator to automatically log function performance.

    Args:
        operation_name: Custom operation name (defaults to function name)
        logger_name: Logger name to use
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            with logger.performance(op_name, function=func.__name__):
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    logger.error(f"Function {func.__name__} failed", error=str(e))
                    raise

        return wrapper
    return decorator