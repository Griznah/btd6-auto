"""
Enhanced logging system for BTD6 automation.

This module provides structured logging, performance timing, and
comprehensive debugging capabilities for reliable automation monitoring.
"""

import logging
import logging.handlers
import os
import time
import functools
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from pathlib import Path

from .config import _get_config_manager


class BTD6Logger:
    """
    Enhanced logger for BTD6 automation with structured logging and performance tracking.

    This class provides operation-specific logging, performance timing, and
    structured log formatting for better debugging and monitoring.
    """

    def __init__(self, name: str = "btd6_auto"):
        """
        Initialize BTD6 logger.

        Args:
            name: Logger name for namespacing
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.config_manager = _get_config_manager()
        self._setup_logging()
        self._performance_timers = {}

    def _setup_logging(self):
        """Set up logging configuration if not already configured."""
        if not self.logger.handlers:
            # Create logs directory
            logs_dir = Path.home() / ".btd6_auto" / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)

            # Set log level from config or default to INFO
            log_level = self._get_log_level()
            self.logger.setLevel(log_level)

            # Create formatters
            detailed_formatter = logging.Formatter(
                fmt='%(asctime)s | %(name)s | %(levelname)8s | %(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            simple_formatter = logging.Formatter(
                fmt='%(asctime)s | %(levelname)8s | %(message)s',
                datefmt='%H:%M:%S'
            )

            # Console handler (INFO and above)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(simple_formatter)
            console_handler.addFilter(lambda record: record.levelno >= logging.INFO)
            self.logger.addHandler(console_handler)

            # File handler (all levels)
            log_file = logs_dir / "btd6_automation.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(detailed_formatter)
            self.logger.addHandler(file_handler)

            # Performance log file (separate file for performance data)
            perf_log_file = logs_dir / "performance.log"
            self.perf_logger = logging.getLogger(f"{self.name}.performance")
            perf_handler = logging.handlers.RotatingFileHandler(
                perf_log_file,
                maxBytes=5*1024*1024,  # 5MB
                backupCount=3
            )
            perf_handler.setFormatter(logging.Formatter(
                fmt='%(asctime)s | %(message)s',
                datefmt='%H:%M:%S'
            ))
            self.perf_logger.addHandler(perf_handler)
            self.perf_logger.setLevel(logging.INFO)
            self.perf_logger.propagate = False  # Don't propagate to root logger

    def _get_log_level(self) -> int:
        """Get log level from configuration or use default."""
        # Could be extended to read from config file
        log_level_name = os.environ.get('BTD6_LOG_LEVEL', 'INFO').upper()
        levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return levels.get(log_level_name, logging.INFO)

    def debug(self, message: str, operation: str = None, **kwargs):
        """Log debug message with optional operation context."""
        context = self._build_context(operation, **kwargs)
        self.logger.debug(f"{message} | {context}" if context else message)

    def info(self, message: str, operation: str = None, **kwargs):
        """Log info message with optional operation context."""
        context = self._build_context(operation, **kwargs)
        self.logger.info(f"{message} | {context}" if context else message)

    def warning(self, message: str, operation: str = None, **kwargs):
        """Log warning message with optional operation context."""
        context = self._build_context(operation, **kwargs)
        self.logger.warning(f"{message} | {context}" if context else message)

    def error(self, message: str, operation: str = None, exc_info: bool = True, **kwargs):
        """Log error message with optional operation context."""
        context = self._build_context(operation, **kwargs)
        full_message = f"{message} | {context}" if context else message
        self.logger.error(full_message, exc_info=exc_info)

    def critical(self, message: str, operation: str = None, **kwargs):
        """Log critical message with optional operation context."""
        context = self._build_context(operation, **kwargs)
        full_message = f"{message} | {context}" if context else message
        self.logger.critical(full_message)

    def _build_context(self, operation: str = None, **kwargs) -> str:
        """Build context string from operation and additional data."""
        parts = []

        if operation:
            parts.append(f"op:{operation}")

        # Add key-value pairs from kwargs
        for key, value in kwargs.items():
            if isinstance(value, (str, int, float, bool)):
                parts.append(f"{key}:{value}")
            elif isinstance(value, (list, tuple)) and len(value) <= 3:
                parts.append(f"{key}:{value}")
            else:
                parts.append(f"{key}:[...]")

        return " | ".join(parts) if parts else ""

    @contextmanager
    def performance_timer(self, operation: str, threshold_ms: float = 100.0):
        """
        Context manager for timing operations and logging performance.

        Args:
            operation: Name of the operation being timed
            threshold_ms: Threshold in milliseconds above which to log warning
        """
        start_time = time.perf_counter()
        timer_key = f"{operation}_{id(self)}"

        try:
            self._performance_timers[timer_key] = start_time
            yield
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000

            # Log performance data
            self.perf_logger.info(f"{operation} | {duration_ms:.2f}ms")

            if duration_ms > threshold_ms:
                self.warning(
                    f"Slow operation detected",
                    operation=operation,
                    duration_ms=duration_ms,
                    threshold_ms=threshold_ms
                )

            self._performance_timers.pop(timer_key, None)

    def log_operation_start(self, operation: str, **kwargs):
        """Log the start of an operation."""
        self.info(f"Starting operation", operation=operation, **kwargs)

    def log_operation_success(self, operation: str, duration_ms: float = None, **kwargs):
        """Log successful completion of an operation."""
        if duration_ms is not None:
            kwargs['duration_ms'] = duration_ms

        self.info(f"Operation completed successfully", operation=operation, **kwargs)

    def log_operation_failure(self, operation: str, error: Exception, **kwargs):
        """Log failure of an operation."""
        error_type = type(error).__name__
        self.error(
            f"Operation failed: {error}",
            operation=operation,
            error_type=error_type,
            **kwargs
        )

    def log_game_event(self, event: str, **kwargs):
        """Log game-specific events."""
        self.info(f"Game event: {event}", event_type="game_event", **kwargs)

    def log_input_event(self, event_type: str, **kwargs):
        """Log input-related events."""
        self.debug(f"Input event: {event_type}", event_type="input_event", **kwargs)

    def log_image_operation(self, operation: str, template_path: str = None, confidence: float = None, **kwargs):
        """Log image recognition operations."""
        log_kwargs = {"image_op": operation}
        if template_path:
            log_kwargs["template"] = os.path.basename(template_path)
        if confidence is not None:
            log_kwargs["confidence"] = f"{confidence:.3f}"

        self.debug(f"Image operation", **log_kwargs, **kwargs)


def get_logger(name: str = "btd6_auto") -> BTD6Logger:
    """
    Get or create a BTD6 logger instance.

    Args:
        name: Logger name

    Returns:
        BTD6Logger instance
    """
    return BTD6Logger(name)


# Global logger instance
_global_logger = None


def get_global_logger() -> BTD6Logger:
    """Get the global BTD6 logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = BTD6Logger()
    return _global_logger


def log_performance(operation: str, threshold_ms: float = 100.0):
    """
    Decorator to log operation performance.

    Args:
        operation: Operation name for logging
        threshold_ms: Threshold for warning about slow operations
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_global_logger()

            with logger.performance_timer(operation, threshold_ms):
                return func(*args, **kwargs)

        return wrapper
    return decorator


def log_operation(operation: str = None, include_timing: bool = True):
    """
    Decorator to log operation start, success/failure, and timing.

    Args:
        operation: Operation name (auto-detected if None)
        include_timing: Whether to include performance timing
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_global_logger()
            op_name = operation or func.__name__

            logger.log_operation_start(op_name)

            start_time = time.perf_counter() if include_timing else None

            try:
                result = func(*args, **kwargs)

                if include_timing and start_time:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    logger.log_operation_success(op_name, duration_ms)

                return result

            except Exception as e:
                if include_timing and start_time:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    logger.log_operation_failure(op_name, e, duration_ms=duration_ms)
                else:
                    logger.log_operation_failure(op_name, e)

                raise

        return wrapper
    return decorator


class LogContext:
    """
    Context manager for logging operation blocks with consistent formatting.

    Useful for grouping related log messages and providing context
    for complex operations.
    """

    def __init__(self, operation: str, logger: Optional[BTD6Logger] = None, **context):
        """
        Initialize log context.

        Args:
            operation: Operation name for context
            logger: Logger instance (uses global if None)
            **context: Additional context key-value pairs
        """
        self.operation = operation
        self.logger = logger or get_global_logger()
        self.context = context
        self.start_time = None

    def __enter__(self):
        """Enter the log context."""
        self.start_time = time.perf_counter()
        self.logger.info(f"Entering operation context", operation=self.operation, **self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the log context."""
        duration_ms = None
        if self.start_time:
            duration_ms = (time.perf_counter() - self.start_time) * 1000

        if exc_type:
            self.logger.error(
                "Operation context exited with exception",
                operation=self.operation,
                exception=type(exc_val).__name__,
                duration_ms=duration_ms,
                **self.context
            )
        else:
            self.logger.info(
                "Operation context completed",
                operation=self.operation,
                duration_ms=duration_ms,
                **self.context
            )

    def log_event(self, event: str, **kwargs):
        """Log an event within this context."""
        all_kwargs = {**self.context, **kwargs}
        self.logger.info(f"Context event: {event}", operation=self.operation, **all_kwargs)

    def log_debug(self, message: str, **kwargs):
        """Log debug message within this context."""
        all_kwargs = {**self.context, **kwargs}
        self.logger.debug(message, operation=self.operation, **all_kwargs)


def setup_global_logging(log_level: str = "INFO", log_to_file: bool = True):
    """
    Set up global logging configuration for BTD6 automation.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to files in addition to console
    """
    # This function can be called to override default logging setup
    logger = get_global_logger()

    # Update log level
    levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    logger.logger.setLevel(levels.get(log_level.upper(), logging.INFO))

    logger.info(f"Global logging configured with level {log_level}")


# Convenience functions for common logging patterns
def log_game_state_change(old_state: str, new_state: str, **kwargs):
    """Log game state changes."""
    logger = get_global_logger()
    logger.log_game_event(
        "state_change",
        old_state=old_state,
        new_state=new_state,
        **kwargs
    )


def log_input_action(action: str, coordinates: tuple = None, key: str = None, **kwargs):
    """Log input actions."""
    logger = get_global_logger()
    logger.log_input_event(action, coordinates=coordinates, key=key, **kwargs)


def log_image_result(template_path: str, confidence: float, success: bool, **kwargs):
    """Log image recognition results."""
    logger = get_global_logger()
    logger.log_image_operation(
        "match_result" if success else "match_failed",
        template_path=template_path,
        confidence=confidence,
        success=success,
        **kwargs
    )
