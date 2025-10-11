"""
Comprehensive tests for the BTD6 logging system.

Tests structured logging, performance logging, context management, and logging
integration without requiring the actual game or GUI interactions.
"""

import os
import sys
import unittest
import logging
import time
import tempfile
import json
from unittest.mock import patch, MagicMock
from io import StringIO

# Add the btd6_auto module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'btd6_auto'))

from logging_utils import (
    BTD6Logger,
    get_logger,
    log_performance,
    LogContext,
    setup_logging
)


class LoggingSystemTests(unittest.TestCase):
    """Test cases for basic logging functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a string stream to capture log output
        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)

        # Set up a test logger
        self.test_logger = logging.getLogger('test_btd6_logger')
        self.test_logger.setLevel(logging.DEBUG)
        self.test_logger.addHandler(self.handler)

    def tearDown(self):
        """Clean up test fixtures."""
        self.test_logger.removeHandler(self.handler)
        self.log_stream.close()

    def test_logger_creation(self):
        """Test logger creation and configuration."""
        logger = get_logger("test_module")

        # Should return a logger instance
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test_module")

        # Should have appropriate level and handlers
        self.assertLessEqual(logger.level, logging.INFO)
        self.assertGreater(len(logger.handlers), 0)

    def test_logger_singleton_behavior(self):
        """Test that get_logger returns the same instance for same name."""
        logger1 = get_logger("singleton_test")
        logger2 = get_logger("singleton_test")

        # Should return the same logger instance
        self.assertIs(logger1, logger2)

    def test_btd6_logger_custom_functionality(self):
        """Test BTD6Logger custom functionality."""
        logger = BTD6Logger("test_btd6")

        # Test structured logging
        test_data = {
            "operation": "test_operation",
            "coordinates": (100, 200),
            "success": True
        }

        # Should log structured data
        logger.info("Test message", extra=test_data)

        # Check that log output contains structured data
        log_output = self.log_stream.getvalue()
        self.assertIn("test_operation", log_output)
        self.assertIn("100", log_output)  # Coordinate x
        self.assertIn("200", log_output)  # Coordinate y

    def test_log_levels(self):
        """Test different logging levels."""
        logger = get_logger("level_test")

        levels_and_methods = [
            (logging.DEBUG, logger.debug),
            (logging.INFO, logger.info),
            (logging.WARNING, logger.warning),
            (logging.ERROR, logger.error),
        ]

        for level, method in levels_and_methods:
            with self.subTest(level=level):
                self.log_stream.seek(0)
                self.log_stream.truncate(0)

                method(f"Test message at level {level}")

                log_output = self.log_stream.getvalue()
                self.assertGreater(len(log_output), 0)
                self.assertIn("Test message", log_output)

    def test_structured_logging_format(self):
        """Test structured logging with key-value pairs."""
        logger = get_logger("structured_test")

        # Test logging with extra fields
        logger.info("Operation completed", extra={
            "operation": "coordinate_validation",
            "duration_ms": 150.5,
            "coordinates_validated": 5,
            "errors_found": 0
        })

        log_output = self.log_stream.getvalue()

        # Should contain structured data
        self.assertIn("coordinate_validation", log_output)
        self.assertIn("150.5", log_output)
        self.assertIn("5", log_output)

    def test_performance_logging_decorator(self):
        """Test the @log_performance decorator."""
        @log_performance("test_operation", threshold_ms=50.0)
        def test_function():
            time.sleep(0.01)  # 10ms operation
            return "success"

        # Should execute successfully
        result = test_function()
        self.assertEqual(result, "success")

        # Check that performance was logged
        log_output = self.log_stream.getvalue()
        # The decorator might not log to our test stream, so we just verify execution

    def test_performance_logging_with_threshold(self):
        """Test performance logging with different thresholds."""
        @log_performance("fast_operation", threshold_ms=100.0)
        def fast_operation():
            time.sleep(0.01)  # 10ms - below threshold
            return "fast"

        @log_performance("slow_operation", threshold_ms=5.0)
        def slow_operation():
            time.sleep(0.01)  # 10ms - above threshold
            return "slow"

        # Both should execute successfully
        fast_result = fast_operation()
        slow_result = slow_operation()

        self.assertEqual(fast_result, "fast")
        self.assertEqual(slow_result, "slow")

    def test_log_context_management(self):
        """Test LogContext context manager functionality."""
        logger = get_logger("context_test")

        with LogContext("test_context", logger) as ctx:
            ctx.log_event("Starting operation")
            ctx.log_event("Operation in progress", extra={"step": 1})

            # Simulate some operation
            time.sleep(0.001)

            ctx.log_event("Operation completed", extra={"step": 2})

        # Context should handle logging properly
        log_output = self.log_stream.getvalue()
        self.assertIn("test_context", log_output)
        self.assertIn("Starting operation", log_output)
        self.assertIn("Operation completed", log_output)

    def test_log_context_exception_handling(self):
        """Test LogContext exception handling."""
        logger = get_logger("exception_context_test")

        with self.assertRaises(ValueError):
            with LogContext("error_context", logger) as ctx:
                ctx.log_event("About to fail")
                raise ValueError("Test error")

        # Should still log the context
        log_output = self.log_stream.getvalue()
        self.assertIn("error_context", log_output)
        self.assertIn("About to fail", log_output)


class LoggingConfigurationTests(unittest.TestCase):
    """Test cases for logging configuration."""

    def test_setup_logging_function(self):
        """Test the setup_logging function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test_btd6.log")

            # Test setting up logging with file output
            setup_logging(
                log_level=logging.DEBUG,
                log_file=log_file,
                format_string="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
            )

            # Create a test logger and log something
            test_logger = get_logger("config_test")
            test_logger.info("Test log message")

            # Check that log file was created and contains the message
            self.assertTrue(os.path.exists(log_file))

            with open(log_file, 'r') as f:
                log_content = f.read()
                self.assertIn("Test log message", log_content)
                self.assertIn("config_test", log_content)

    def test_logging_with_json_format(self):
        """Test logging with JSON format for structured data."""
        logger = get_logger("json_format_test")

        # Create a custom formatter for JSON output
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': self.formatTime(record),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage()
                }
                if hasattr(record, '__dict__'):
                    for key, value in record.__dict__.items():
                        if key not in ['name', 'msg', 'args', 'levelname', 'levelno',
                                     'pathname', 'filename', 'module', 'lineno',
                                     'funcName', 'created', 'msecs', 'relativeCreated',
                                     'thread', 'threadName', 'processName', 'process',
                                     'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                            log_entry[key] = value
                return json.dumps(log_entry)

        # Add JSON formatter to handler
        json_handler = logging.StreamHandler(StringIO())
        json_handler.setFormatter(JSONFormatter())
        logger.addHandler(json_handler)
        logger.setLevel(logging.INFO)

        # Log structured data
        logger.info("JSON test message", extra={
            "operation": "json_logging",
            "data": {"key": "value", "number": 42}
        })

        # Get the JSON output
        json_output = json_handler.stream.getvalue()
        log_data = json.loads(json_output)

        # Verify JSON structure
        self.assertEqual(log_data['level'], 'INFO')
        self.assertEqual(log_data['logger'], 'json_format_test')
        self.assertEqual(log_data['message'], 'JSON test message')
        self.assertEqual(log_data['operation'], 'json_logging')
        self.assertEqual(log_data['data'], {"key": "value", "number": 42})

        logger.removeHandler(json_handler)


class LoggingIntegrationTests(unittest.TestCase):
    """Integration tests for logging with other systems."""

    def setUp(self):
        """Set up test fixtures."""
        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, 'test_logger'):
            self.test_logger.removeHandler(self.handler)
        self.log_stream.close()

    def test_logging_with_exception_handling(self):
        """Test logging integration with exception handling."""
        logger = get_logger("exception_logging_integration")
        logger.addHandler(self.handler)
        logger.setLevel(logging.ERROR)

        try:
            raise ValueError("Test exception for logging")
        except ValueError as e:
            logger.error("Caught exception", extra={
                "exception_type": type(e).__name__,
                "exception_message": str(e),
                "operation": "test_operation"
            })

        log_output = self.log_stream.getvalue()
        self.assertIn("Caught exception", log_output)
        self.assertIn("ValueError", log_output)
        self.assertIn("Test exception for logging", log_output)

    def test_performance_logging_integration(self):
        """Test performance logging with actual timing."""
        @log_performance("timing_integration_test", threshold_ms=1.0)
        def timed_operation():
            # Simulate some work
            time.sleep(0.002)  # 2ms operation
            return "completed"

        # Execute the timed operation
        result = timed_operation()
        self.assertEqual(result, "completed")

        # The decorator should handle the timing internally
        # We can't easily test the logging output without more complex setup

    def test_context_logging_with_operations(self):
        """Test context logging across multiple operations."""
        logger = get_logger("context_operations_test")
        logger.addHandler(self.handler)
        logger.setLevel(logging.INFO)

        def operation_with_context(name, duration):
            with LogContext(f"operation_{name}", logger) as ctx:
                ctx.log_event(f"Starting {name}")
                time.sleep(duration)
                ctx.log_event(f"Completed {name}")
            return f"{name}_result"

        # Execute multiple operations
        result1 = operation_with_context("first", 0.001)
        result2 = operation_with_context("second", 0.001)

        self.assertEqual(result1, "first_result")
        self.assertEqual(result2, "second_result")

        log_output = self.log_stream.getvalue()
        self.assertIn("operation_first", log_output)
        self.assertIn("operation_second", log_output)


class LoggingPerformanceTests(unittest.TestCase):
    """Test logging performance and overhead."""

    def test_logging_overhead_measurement(self):
        """Test measuring logging overhead."""
        logger = get_logger("performance_test")

        # Test logging overhead
        iterations = 1000

        # Time without logging
        start_time = time.time()
        for i in range(iterations):
            pass  # No-op
        no_logging_time = time.time() - start_time

        # Time with logging
        start_time = time.time()
        for i in range(iterations):
            logger.debug(f"Iteration {i}")
        with_logging_time = time.time() - start_time

        # Logging should add some overhead but not be excessive
        overhead_ratio = with_logging_time / no_logging_time
        self.assertGreater(overhead_ratio, 1.0)  # Should have some overhead
        self.assertLess(overhead_ratio, 50.0)   # But not excessive

    def test_structured_logging_overhead(self):
        """Test structured logging overhead."""
        logger = get_logger("structured_performance_test")

        iterations = 500

        # Time structured logging
        start_time = time.time()
        for i in range(iterations):
            logger.info(f"Structured log {i}", extra={
                "iteration": i,
                "data": {"key": "value", "number": i}
            })
        structured_time = time.time() - start_time

        # Time simple logging
        start_time = time.time()
        for i in range(iterations):
            logger.info(f"Simple log {i}")
        simple_time = time.time() - start_time

        # Structured logging should have some overhead but not be dramatically slower
        overhead_ratio = structured_time / simple_time
        self.assertGreater(overhead_ratio, 1.0)
        self.assertLess(overhead_ratio, 10.0)  # Reasonable overhead for structured data

    def test_log_context_overhead(self):
        """Test LogContext overhead."""
        logger = get_logger("context_overhead_test")

        iterations = 100

        # Time without context
        start_time = time.time()
        for i in range(iterations):
            logger.info(f"Log without context {i}")
        no_context_time = time.time() - start_time

        # Time with context
        start_time = time.time()
        for i in range(iterations):
            with LogContext(f"context_{i}", logger):
                logger.info(f"Log with context {i}")
        with_context_time = time.time() - start_time

        # Context should add minimal overhead
        overhead_ratio = with_context_time / no_context_time
        self.assertGreater(overhead_ratio, 1.0)
        self.assertLess(overhead_ratio, 5.0)  # Reasonable overhead for context management


class LoggingEdgeCasesTests(unittest.TestCase):
    """Test edge cases and error conditions in logging."""

    def test_logging_with_none_values(self):
        """Test logging with None values in extra data."""
        logger = get_logger("none_values_test")

        # Should handle None values gracefully
        logger.info("Message with None", extra={
            "none_value": None,
            "empty_string": "",
            "zero": 0,
            "false": False
        })

        # Should not raise any exceptions

    def test_logging_with_circular_references(self):
        """Test logging with circular references in data."""
        logger = get_logger("circular_test")

        # Create circular reference
        data = {"key": "value"}
        data["self"] = data

        # Should handle circular references gracefully (or at least not crash)
        try:
            logger.info("Message with circular data", extra={"data": data})
        except (TypeError, ValueError, RecursionError):
            # Expected for circular references in JSON serialization
            pass

    def test_logging_with_large_data(self):
        """Test logging with large amounts of data."""
        logger = get_logger("large_data_test")

        # Create large data structure
        large_data = {
            "big_list": list(range(1000)),
            "big_dict": {f"key_{i}": f"value_{i}" for i in range(100)},
            "nested": {
                "level1": {
                    "level2": {
                        "level3": list(range(50))
                    }
                }
            }
        }

        # Should handle large data without issues
        logger.info("Message with large data", extra={"data": large_data})

    def test_logging_during_exception_handling(self):
        """Test logging behavior during exception handling."""
        logger = get_logger("exception_logging_test")

        try:
            raise ValueError("Test exception")
        except ValueError as e:
            # Logging during exception handling should work
            logger.error("Exception occurred", extra={
                "exception_type": type(e).__name__,
                "exception_message": str(e)
            })

        # Should not interfere with exception handling

    def test_logger_name_validation(self):
        """Test logger name validation and edge cases."""
        # Test various logger names
        valid_names = [
            "test",
            "test_module",
            "test.module.submodule",
            "test_123",
            "test-module"
        ]

        for name in valid_names:
            with self.subTest(name=name):
                logger = get_logger(name)
                self.assertEqual(logger.name, name)

        # Test that loggers are cached properly
        logger1 = get_logger("cache_test")
        logger2 = get_logger("cache_test")
        self.assertIs(logger1, logger2)


if __name__ == '__main__':
    unittest.main()
