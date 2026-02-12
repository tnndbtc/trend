"""
Structured logging configuration for the Trend Intelligence Platform.

This module provides structured logging with JSON formatting, context management,
and integration with external log aggregation systems.
"""

import logging
import sys
import os
import json
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
from functools import wraps


# Context variable for request tracking
request_context: ContextVar[Dict[str, Any]] = ContextVar("request_context", default={})


# ============================================================================
# JSON Formatter
# ============================================================================

class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Outputs log records as JSON objects with standard fields:
    - timestamp: ISO 8601 timestamp
    - level: Log level (INFO, WARNING, ERROR, etc.)
    - logger: Logger name
    - message: Log message
    - context: Request context (if available)
    - extra: Any extra fields passed to the logger
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add request context if available
        ctx = request_context.get()
        if ctx:
            log_data["context"] = ctx

        # Add any extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


# ============================================================================
# Logging Setup
# ============================================================================

def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = True,
):
    """
    Setup application logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for file logging
        json_format: Use JSON formatting (True) or plain text (False)

    Example:
        setup_logging(level="INFO", log_file="/var/log/trends.log", json_format=True)
    """
    # Get log level
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers = []

    # Create formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set levels for noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.WARNING)

    logging.info(f"Logging configured: level={level}, json={json_format}, file={log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Application started")
    """
    return logging.getLogger(name)


# ============================================================================
# Context Management
# ============================================================================

class log_context:
    """
    Context manager for adding context to all log messages within a scope.

    Example:
        with log_context(request_id="123", user_id="456"):
            logger.info("Processing request")
            # Logs will include request_id and user_id
    """

    def __init__(self, **kwargs):
        """
        Initialize log context.

        Args:
            **kwargs: Context key-value pairs
        """
        self.context = kwargs
        self.token = None

    def __enter__(self):
        """Enter context and set context variables."""
        current_context = request_context.get().copy()
        current_context.update(self.context)
        self.token = request_context.set(current_context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and reset context variables."""
        request_context.reset(self.token)


def add_log_context(**kwargs):
    """
    Add context to current request context.

    Args:
        **kwargs: Context key-value pairs

    Example:
        add_log_context(user_id="123", action="login")
    """
    current_context = request_context.get().copy()
    current_context.update(kwargs)
    request_context.set(current_context)


def clear_log_context():
    """Clear all log context."""
    request_context.set({})


# ============================================================================
# Decorators
# ============================================================================

def log_function_call(logger: Optional[logging.Logger] = None):
    """
    Decorator to log function calls with parameters and execution time.

    Args:
        logger: Optional logger instance (uses function's module logger if None)

    Example:
        @log_function_call()
        async def my_function(param1, param2):
            pass
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)

            func_name = func.__name__
            logger.debug(f"Entering {func_name}", extra={
                "extra_fields": {"args": str(args)[:100], "kwargs": str(kwargs)[:100]}
            })

            start_time = datetime.utcnow()
            try:
                result = await func(*args, **kwargs)
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.debug(f"Exiting {func_name}", extra={
                    "extra_fields": {"duration_seconds": duration}
                })
                return result

            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.error(f"Error in {func_name}: {e}", extra={
                    "extra_fields": {"duration_seconds": duration, "error": str(e)}
                }, exc_info=True)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)

            func_name = func.__name__
            logger.debug(f"Entering {func_name}")

            start_time = datetime.utcnow()
            try:
                result = func(*args, **kwargs)
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.debug(f"Exiting {func_name}", extra={
                    "extra_fields": {"duration_seconds": duration}
                })
                return result

            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.error(f"Error in {func_name}: {e}", extra={
                    "extra_fields": {"duration_seconds": duration, "error": str(e)}
                }, exc_info=True)
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# Helper Functions
# ============================================================================

def log_error(logger: logging.Logger, message: str, error: Exception, **kwargs):
    """
    Log an error with exception details and context.

    Args:
        logger: Logger instance
        message: Error message
        error: Exception object
        **kwargs: Additional context fields
    """
    logger.error(message, extra={
        "extra_fields": {
            "error_type": type(error).__name__,
            "error_message": str(error),
            **kwargs,
        }
    }, exc_info=True)


def log_warning(logger: logging.Logger, message: str, **kwargs):
    """
    Log a warning with context.

    Args:
        logger: Logger instance
        message: Warning message
        **kwargs: Additional context fields
    """
    logger.warning(message, extra={"extra_fields": kwargs})


def log_info(logger: logging.Logger, message: str, **kwargs):
    """
    Log an info message with context.

    Args:
        logger: Logger instance
        message: Info message
        **kwargs: Additional context fields
    """
    logger.info(message, extra={"extra_fields": kwargs})


# ============================================================================
# Audit Logging
# ============================================================================

class AuditLogger:
    """
    Specialized logger for audit events.

    Audit logs track security-relevant events like authentication,
    authorization, data access, and configuration changes.
    """

    def __init__(self):
        """Initialize audit logger."""
        self.logger = get_logger("audit")
        self.logger.setLevel(logging.INFO)

    def log_auth_attempt(self, user: str, success: bool, ip_address: Optional[str] = None):
        """Log authentication attempt."""
        self.logger.info("Authentication attempt", extra={
            "extra_fields": {
                "event_type": "auth_attempt",
                "user": user,
                "success": success,
                "ip_address": ip_address,
            }
        })

    def log_api_access(self, user: str, endpoint: str, method: str, status_code: int):
        """Log API access."""
        self.logger.info("API access", extra={
            "extra_fields": {
                "event_type": "api_access",
                "user": user,
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
            }
        })

    def log_data_access(self, user: str, resource_type: str, resource_id: str, action: str):
        """Log data access."""
        self.logger.info("Data access", extra={
            "extra_fields": {
                "event_type": "data_access",
                "user": user,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
            }
        })

    def log_config_change(self, user: str, config_key: str, old_value: Any, new_value: Any):
        """Log configuration change."""
        self.logger.info("Configuration change", extra={
            "extra_fields": {
                "event_type": "config_change",
                "user": user,
                "config_key": config_key,
                "old_value": str(old_value),
                "new_value": str(new_value),
            }
        })


# Global audit logger instance
audit_logger = AuditLogger()


# ============================================================================
# Log Levels Configuration
# ============================================================================

def set_log_level(logger_name: str, level: str):
    """
    Set log level for a specific logger.

    Args:
        logger_name: Name of the logger
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Example:
        set_log_level("trend_agent.ingestion", "DEBUG")
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper()))


def get_log_level(logger_name: str) -> str:
    """
    Get current log level for a logger.

    Args:
        logger_name: Name of the logger

    Returns:
        Log level name
    """
    logger = logging.getLogger(logger_name)
    return logging.getLevelName(logger.level)


# ============================================================================
# Initialize Default Logging
# ============================================================================

# Setup logging from environment variables if available
if os.getenv("LOG_LEVEL"):
    setup_logging(
        level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE"),
        json_format=os.getenv("LOG_JSON", "true").lower() == "true",
    )
