"""
Retry utilities for BTD6 automation.

This module provides retry decorators and utilities for handling
transient failures in automation operations.
"""

import functools
import logging
import random
import time
from typing import Callable, Any, List, Type, Union

from .exceptions import RetryExhaustedError, BTD6AutomationError


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Union[Type[Exception], List[Type[Exception]]] = None,
    operation_name: str = None
):
    """
    Decorator that implements retry logic with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (including initial attempt)
        base_delay: Base delay in seconds before first retry
        max_delay: Maximum delay in seconds between retries
        backoff_factor: Factor by which delay increases each retry
        jitter: Whether to add random jitter to delay times
        retryable_exceptions: Exception types that should trigger retries
        operation_name: Name of the operation for logging (auto-detected if None)

    Returns:
        Decorated function that implements retry logic

    Raises:
        RetryExhaustedError: When all retry attempts are exhausted
        Original exception: If exception is not retryable
    """

    # Default retryable exceptions
    if retryable_exceptions is None:
        retryable_exceptions = [
            ConnectionError,
            TimeoutError,
            OSError,  # Covers various I/O errors
            BTD6AutomationError,  # Base class for our custom errors
        ]
    elif isinstance(retryable_exceptions, type):
        retryable_exceptions = [retryable_exceptions]

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Auto-detect operation name from function if not provided
            op_name = operation_name or func.__name__

            logger = logging.getLogger(__name__)
            last_exception = None

            # Initial attempt + retries
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.info(f"Retry attempt {attempt}/{max_retries - 1} for {op_name}")

                    result = func(*args, **kwargs)

                    if attempt > 0:
                        logger.info(f"Operation {op_name} succeeded on attempt {attempt + 1}")

                    return result

                except Exception as e:
                    last_exception = e

                    # Check if exception is retryable
                    is_retryable = any(isinstance(e, exc_type) for exc_type in retryable_exceptions)

                    if not is_retryable:
                        raise

                    if attempt == max_retries - 1:
                        if attempt > 0:
                            logger.error(f"Operation {op_name} failed after {attempt + 1} attempts")
                        break

                    # Calculate delay for next retry
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)

                    # Add jitter to prevent thundering herd
                    if jitter:
                        jitter_amount = delay * 0.1  # 10% jitter
                        delay += random.uniform(-jitter_amount, jitter_amount)

                    logger.warning(
                        f"Operation {op_name} failed on attempt {attempt + 1}: {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )

                    time.sleep(delay)

            # All retries exhausted
            raise RetryExhaustedError(
                message=f"Operation '{op_name}' failed after {max_retries} attempts",
                attempts=max_retries,
                last_error=last_exception,
                operation=op_name
            )
        return wrapper

    return decorator


def retry_with_config(func: Callable) -> Callable:
    """
    Decorator that uses configuration values for retry parameters.

    This decorator automatically uses retry settings from the ConfigManager
    for max_retries and retry_delay values.

    Returns:
        Decorated function with configuration-based retry logic
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Import here to avoid circular imports
        from .config import _get_config_manager

        config_manager = _get_config_manager()
        max_retries = config_manager.get_setting('max_retries') or 3
        retry_delay = config_manager.get_setting('retry_delay') or 1.0

        # Use the standard retry decorator with config values
        return retry(
            max_retries=max_retries,
            base_delay=retry_delay,
            operation_name=func.__name__
        )(func)(*args, **kwargs)

    return wrapper


class RetryContext:
    """
    Context manager for retry operations with custom logic.

    Useful when you need more control over retry behavior or want to
    implement custom retry logic for specific operations.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Union[Type[Exception], List[Type[Exception]]] = None,
        operation_name: str = None
    ):
        """
        Initialize retry context.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds before first retry
            max_delay: Maximum delay in seconds between retries
            backoff_factor: Factor by which delay increases each retry
            jitter: Whether to add random jitter to delay times
            retryable_exceptions: Exception types that should trigger retries
            operation_name: Name of the operation for logging
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            ConnectionError, TimeoutError, OSError, BTD6AutomationError
        ]
        if isinstance(self.retryable_exceptions, type):
            self.retryable_exceptions = [self.retryable_exceptions]

        self.operation_name = operation_name
        self.logger = logging.getLogger(__name__)
        self.attempt = 0
        self.last_exception = None

    def __enter__(self):
        """Enter the retry context."""
        return self

    def run(self, callable: Callable, *args, **kwargs) -> Any:
        """
        Execute a callable with retry logic using exponential backoff.

        Args:
            callable: Function to execute
            *args: Positional arguments for the callable
            **kwargs: Keyword arguments for the callable

        Returns:
            Function result on success

        Raises:
            RetryExhaustedError: When all retry attempts are exhausted
            Original exception: If retries exhausted or exception is not retryable
        """
        # Reset attempt counter for new run
        self.attempt = 0
        self.last_exception = None

        op_name = self.operation_name or getattr(callable, '__name__', 'operation')
        logger = logging.getLogger(__name__)

        # Attempt loop
        while self.attempt < self.max_retries:
            try:
                logger.info(f"Attempt {self.attempt + 1}/{self.max_retries} for {op_name}")

                result = callable(*args, **kwargs)

                if self.attempt > 0:
                    logger.info(f"Operation {op_name} succeeded on attempt {self.attempt + 1}")

                return result

            except Exception as e:
                self.last_exception = e

                # Check if exception is retryable
                is_retryable = any(isinstance(e, exc_type) for exc_type in self.retryable_exceptions)

                if not is_retryable:
                    raise

                if self.attempt == self.max_retries - 1:
                    if self.attempt > 0:
                        logger.exception(f"Operation {op_name} failed after {self.attempt + 1} attempts")
                    raise RetryExhaustedError(
                        message=f"Operation '{op_name}' failed after {self.attempt + 1} attempts",
                        attempts=self.attempt + 1,
                        last_error=e,
                        operation=op_name
                    ) from e
                # Calculate delay for next retry
                delay = min(self.base_delay * (self.backoff_factor ** self.attempt), self.max_delay)

                # Add jitter to prevent thundering herd
                if self.jitter:
                    jitter_amount = delay * 0.1  # 10% jitter
                    delay += random.uniform(-jitter_amount, jitter_amount)

                logger.warning(
                    f"Operation {op_name} failed on attempt {self.attempt + 1}: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )

                time.sleep(delay)
                self.attempt += 1

        # This should never be reached due to the exception handling above
        raise RuntimeError("Unexpected end of retry loop")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the retry context, handling any exceptions.

        Args:
            exc_type: Type of the exception that occurred
            exc_val: The exception instance
            exc_tb: Traceback object

        Returns:
            False to suppress the exception
        """
        if exc_type is None:
            # No exception, operation succeeded
            return False

        # Check if exception is retryable
        is_retryable = any(issubclass(exc_type, exc_class) for exc_class in self.retryable_exceptions)

        if not is_retryable or self.attempt >= self.max_retries - 1:
            # Not retryable or last attempt, propagate the exception
            return False

        # For context manager usage, we don't suppress exceptions
        # The retry logic should be handled by the explicit run() method
        return False

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function within the retry context.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Function result on success

        Raises:
            RetryExhaustedError: When all retry attempts are exhausted
        """
        while self.attempt < self.max_retries:
            try:
                result = func(*args, **kwargs)

                if self.attempt > 0:
                    op_name = self.operation_name or func.__name__
                    self.logger.info(f"{op_name} succeeded on attempt {self.attempt + 1}")

                return result

            except Exception as e:
                self.last_exception = e

                # Check if exception is retryable
                is_retryable = any(isinstance(e, exc_type) for exc_type in self.retryable_exceptions)

                if not is_retryable or self.attempt == self.max_retries - 1:
                    # Not retryable or last attempt
                    if self.attempt > 0:
                        op_name = self.operation_name or func.__name__
                        self.logger.error(f"{op_name} failed after {self.attempt + 1} attempts")

                    if isinstance(e, BTD6AutomationError):
                        raise RetryExhaustedError(
                            message=f"Operation '{func.__name__}' failed after {self.attempt + 1} attempts",
                            attempts=self.attempt + 1,
                            last_error=e,
                            operation=func.__name__
                        ) from e
                    else:
                        raise

                # Calculate delay for next retry
                delay = min(self.base_delay * (self.backoff_factor ** self.attempt), self.max_delay)

                if self.jitter:
                    jitter_amount = delay * 0.1
                    delay += random.uniform(-jitter_amount, jitter_amount)

                op_name = self.operation_name or func.__name__
                self.logger.warning(
                    f"{op_name} failed on attempt {self.attempt + 1}: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )

                time.sleep(delay)
                self.attempt += 1

        # This should never be reached due to the exception handling above
        raise RuntimeError("Unexpected end of retry loop")


def is_retryable_error(error: Exception, retryable_exceptions: List[Type[Exception]] = None) -> bool:
    """
    Check if an error should be retried based on its type.

    Args:
        error: The exception that occurred
        retryable_exceptions: List of exception types that should be retried

    Returns:
        True if the error should be retried, False otherwise
    """
    if retryable_exceptions is None:
        retryable_exceptions = [ConnectionError, TimeoutError, OSError, BTD6AutomationError]

    return any(isinstance(error, exc_type) for exc_type in retryable_exceptions)
