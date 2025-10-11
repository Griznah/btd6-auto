"""
Performance tests for the BTD6 automation system.

Tests performance characteristics, memory usage, timing, and scalability
of various components without requiring the actual game or GUI interactions.
"""

import os
import sys
import time
import gc
import unittest
from unittest.mock import patch, MagicMock

# Add the btd6_auto module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "btd6_auto"))

from config import ConfigManager
from validation import CoordinateValidator, InputValidator
from retry_utils import retry, RetryContext
from logging_utils import get_logger, log_performance, LogContext
from recovery import RecoveryManager, RecoveryStrategy


class ConfigurationPerformanceTests(unittest.TestCase):
    """Test configuration system performance."""

    def test_config_loading_performance(self):
        """Test configuration loading performance."""
        # Test loading a typical config file
        config_path = os.path.join(
            os.path.dirname(__file__), "test_data", "configs", "valid_config.json"
        )

        # Time multiple config loads
        iterations = 100
        start_time = time.time()

        for _ in range(iterations):
            config = ConfigManager(config_path)
            # Access some settings to ensure full loading
            config.get_setting("monkey_coords")
            config.get_setting("hero_type")

        total_time = time.time() - start_time
        avg_time = total_time / iterations

        # Should be reasonably fast
        self.assertLess(avg_time, 0.01)  # Less than 10ms per load

    def test_config_setting_updates_performance(self):
        """Test configuration setting update performance."""
        config = ConfigManager()

        # Time multiple setting updates
        iterations = 1000
        start_time = time.time()

        for i in range(iterations):
            config.update_setting("monkey_coords", [i % 1000, i % 800])
            config.get_setting("monkey_coords")

        total_time = time.time() - start_time
        avg_time = total_time / iterations

        # Should be very fast
        self.assertLess(avg_time, 0.001)  # Less than 1ms per update

    def test_config_memory_usage(self):
        """Test configuration memory usage."""
        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Create many config managers
        configs = []
        for i in range(100):
            config = ConfigManager()
            config.update_setting("test_setting", f"value_{i}")
            configs.append(config)

        # Force garbage collection
        gc.collect()
        after_objects = len(gc.get_objects())

        # Memory usage should be reasonable
        objects_created = after_objects - initial_objects
        self.assertLess(objects_created, 500)  # Should not create excessive objects

        # Clean up
        del configs
        gc.collect()


class ValidationPerformanceTests(unittest.TestCase):
    """Test validation system performance."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = CoordinateValidator()
        self.input_validator = InputValidator()

    def test_coordinate_validation_performance(self):
        """Test coordinate validation performance."""
        test_coordinates = [(x, y) for x in range(100) for y in range(100)]

        # Time validation of many coordinates
        iterations = len(test_coordinates)
        start_time = time.time()

        for coords in test_coordinates:
            self.validator.validate_coordinates(coords, "performance_test")

        total_time = time.time() - start_time
        avg_time = total_time / iterations

        # Should be very fast
        self.assertLess(avg_time, 0.0001)  # Less than 0.1ms per validation

    def test_batch_validation_performance(self):
        """Test batch validation performance."""
        # Create large batch of coordinates
        coordinate_batch = [(x, y) for x in range(500) for y in range(400)]

        # Time batch validation
        start_time = time.time()
        validated_batch = self.validator.validate_coordinates_batch(
            coordinate_batch, "batch_performance_test"
        )
        total_time = time.time() - start_time

        # Should validate all coordinates
        self.assertEqual(len(validated_batch), len(coordinate_batch))

        # Should be reasonably fast for large batches
        self.assertLess(total_time, 0.1)  # Less than 100ms for 200k coordinates

    def test_input_validation_performance(self):
        """Test input validation performance."""
        test_inputs = [
            ("Easy", "difficulty"),
            ("Monkey Meadow", "map"),
            ("Standard", "mode"),
            ("q", "key"),
        ] * 1000  # 4000 total validations

        start_time = time.time()

        for value, input_type in test_inputs:
            if input_type == "difficulty":
                self.input_validator.validate_difficulty(value, "perf_test")
            elif input_type == "map":
                self.input_validator.validate_map_name(value, "perf_test")
            elif input_type == "mode":
                self.input_validator.validate_mode(value, "perf_test")
            elif input_type == "key":
                self.input_validator.validate_key(value, "perf_test")

        total_time = time.time() - start_time
        avg_time = total_time / len(test_inputs)

        # Should be very fast
        self.assertLess(avg_time, 0.0001)  # Less than 0.1ms per validation


class RetryPerformanceTests(unittest.TestCase):
    """Test retry mechanism performance."""

    def test_retry_overhead_performance(self):
        """Test retry mechanism overhead."""

        @retry(max_retries=3, base_delay=0.001)
        def simple_operation():
            return "success"

        # Time operation without retry decorator
        def no_retry_operation():
            return "success"

        # Time with retry (successful operation)
        iterations = 1000
        start_time = time.time()
        for _ in range(iterations):
            no_retry_operation()
        no_retry_time = time.time() - start_time

        start_time = time.time()
        for _ in range(iterations):
            simple_operation()
        retry_time = time.time() - start_time

        # Retry should add minimal overhead for successful operations
        overhead_ratio = retry_time / no_retry_time
        self.assertLess(overhead_ratio, 2.0)  # Less than 2x overhead

    def test_retry_with_failures_performance(self):
        """Test retry performance when failures occur."""
        attempt_count = 0

        @retry(max_retries=5, base_delay=0.001)
        def failing_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Temporary failure")
            return "success"

        with patch("time.sleep") as mock_sleep:
            start_time = time.time()
            result = failing_operation()
            total_time = time.time() - start_time

        self.assertEqual(result, "success")
        self.assertEqual(attempt_count, 3)

        # Should have called sleep for delays
        self.assertEqual(mock_sleep.call_count, 2)  # Two delays for three attempts

        # Total time should include delays
        self.assertGreater(total_time, 0.001)  # Should take some time due to delays

    def test_retry_context_performance(self):
        """Test RetryContext performance."""
        context = RetryContext("performance_test", max_retries=10)

        # Time recording many attempts
        iterations = 1000
        start_time = time.time()

        for i in range(iterations):
            strategy = RecoveryStrategy(f"strategy_{i % 10}")
            context.record_attempt(strategy, i % 3 == 0, 0.001)

        total_time = time.time() - start_time
        avg_time = total_time / iterations

        # Should be very fast to record attempts
        self.assertLess(avg_time, 0.0001)  # Less than 0.1ms per record


class LoggingPerformanceTests(unittest.TestCase):
    """Test logging system performance."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = get_logger("performance_logging_test")

    def test_logging_overhead(self):
        """Test logging overhead."""
        # Time without logging
        iterations = 10000
        start_time = time.time()
        for i in range(iterations):
            pass  # No-op
        no_logging_time = time.time() - start_time

        # Time with logging
        start_time = time.time()
        for i in range(iterations):
            self.logger.debug(f"Debug message {i}")
        debug_logging_time = time.time() - start_time

        # Time with structured logging
        start_time = time.time()
        for i in range(iterations):
            self.logger.info(
                f"Info message {i}", extra={"iteration": i, "data": {"key": "value"}}
            )
        structured_logging_time = time.time() - start_time

        # Logging should add overhead but not be excessive
        debug_overhead = debug_logging_time / no_logging_time
        structured_overhead = structured_logging_time / no_logging_time

        self.assertGreater(debug_overhead, 1.0)  # Should have some overhead
        self.assertGreater(structured_overhead, 1.0)  # Should have some overhead
        self.assertLess(debug_overhead, 20.0)  # But not excessive
        self.assertLess(structured_overhead, 30.0)  # But not excessive

    def test_log_context_performance(self):
        """Test LogContext performance."""
        # Time without context
        iterations = 1000
        start_time = time.time()
        for i in range(iterations):
            self.logger.info(f"Message without context {i}")
        no_context_time = time.time() - start_time

        # Time with context
        start_time = time.time()
        for i in range(iterations):
            with LogContext(f"context_{i}", self.logger):
                self.logger.info(f"Message with context {i}")
        with_context_time = time.time() - start_time

        # Context should add minimal overhead
        overhead_ratio = with_context_time / no_context_time
        self.assertGreater(overhead_ratio, 1.0)
        self.assertLess(
            overhead_ratio, 3.0
        )  # Reasonable overhead for context management

    def test_performance_logging_decorator_overhead(self):
        """Test @log_performance decorator overhead."""

        @log_performance("test_operation", threshold_ms=1.0)
        def test_function():
            time.sleep(0.001)  # 1ms operation
            return "result"

        # Time without decorator
        def plain_function():
            time.sleep(0.001)
            return "result"

        # Time function calls
        iterations = 100
        start_time = time.time()
        for _ in range(iterations):
            plain_function()
        plain_time = time.time() - start_time

        start_time = time.time()
        for _ in range(iterations):
            test_function()
        decorated_time = time.time() - start_time

        # Decorator should add minimal overhead
        overhead_ratio = decorated_time / plain_time
        self.assertGreater(overhead_ratio, 1.0)
        self.assertLess(overhead_ratio, 2.0)  # Reasonable overhead


class RecoveryPerformanceTests(unittest.TestCase):
    """Test recovery system performance."""

    def setUp(self):
        """Set up test fixtures."""
        self.recovery_manager = RecoveryManager()

    def test_recovery_strategy_registration_performance(self):
        """Test recovery strategy registration performance."""
        # Time registering many strategies
        iterations = 1000
        start_time = time.time()

        for i in range(iterations):
            strategy = RecoveryStrategy(f"strategy_{i}", priority=i % 10)
            self.recovery_manager.register_strategy(strategy)

        total_time = time.time() - start_time
        avg_time = total_time / iterations

        # Should be very fast
        self.assertLess(avg_time, 0.0001)  # Less than 0.1ms per registration

    def test_recovery_attempt_performance(self):
        """Test recovery attempt performance."""
        # Set up a strategy
        strategy = RecoveryStrategy("performance_test")
        strategy.execute = MagicMock(return_value=True)
        self.recovery_manager.register_strategy(strategy)

        # Time many recovery attempts
        iterations = 1000
        start_time = time.time()

        for i in range(iterations):
            context = RecoveryContext(f"operation_{i}")
            self.recovery_manager.attempt_recovery(context, "performance_test")

        total_time = time.time() - start_time
        avg_time = total_time / iterations

        # Should be reasonably fast
        self.assertLess(avg_time, 0.001)  # Less than 1ms per attempt

    def test_recovery_manager_sorting_performance(self):
        """Test recovery manager strategy sorting performance."""
        # Register many strategies with different priorities
        for i in range(100):
            strategy = RecoveryStrategy(f"strategy_{i}", priority=i)
            self.recovery_manager.register_strategy(strategy)

        # Time getting sorted strategies
        iterations = 1000
        start_time = time.time()

        for _ in range(iterations):
            available = self.recovery_manager.get_available_strategies()
            self.assertEqual(len(available), 100)

        total_time = time.time() - start_time
        avg_time = total_time / iterations

        # Should be fast to sort 100 strategies
        self.assertLess(avg_time, 0.001)  # Less than 1ms per sort


class SystemScalabilityTests(unittest.TestCase):
    """Test system scalability with large datasets."""

    def test_large_configuration_files(self):
        """Test handling large configuration files."""
        # Create a large configuration with many settings
        large_config = {}

        # Add many coordinate settings
        for i in range(1000):
            large_config[f"coord_set_{i}"] = [i * 10, i * 10]

        # Add many string settings
        for i in range(500):
            large_config[f"string_setting_{i}"] = f"value_{i}" * 10  # Long strings

        # Time loading large config
        import json
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(large_config, f)
            config_path = f.name

        try:
            start_time = time.time()
            config_manager = ConfigManager(config_path)
            load_time = time.time() - start_time

            # Should load reasonably quickly
            self.assertLess(load_time, 0.1)  # Less than 100ms

            # Should be able to access settings
            self.assertEqual(config_manager.get_setting("coord_set_500"), (5000, 5000))

        finally:
            os.unlink(config_path)

    def test_large_validation_batches(self):
        """Test validation of large coordinate batches."""
        validator = CoordinateValidator()

        # Create very large batch of coordinates
        large_batch = []
        for x in range(1000):
            for y in range(800):
                large_batch.append((x, y))

        # Time batch validation
        start_time = time.time()
        validated_batch = validator.validate_coordinates_batch(
            large_batch, "scalability_test"
        )
        total_time = time.time() - start_time

        # Should validate all coordinates
        self.assertEqual(len(validated_batch), len(large_batch))

        # Should handle large batches reasonably
        self.assertLess(total_time, 1.0)  # Less than 1 second for 800k coordinates

    def test_concurrent_performance(self):
        """Test performance under concurrent load."""
        import threading
        import queue

        def performance_worker(worker_id):
            try:
                # Each worker performs various operations
                config = ConfigManager()
                validator = CoordinateValidator()

                # Perform some operations
                for i in range(100):
                    coords = config.get_setting("monkey_coords")
                    validated = validator.validate_coordinates(
                        coords, f"worker_{worker_id}"
                    )

                return f"worker_{worker_id}_success"

            except Exception as e:
                return f"worker_{worker_id}_error: {e}"

        # Start multiple concurrent workers
        results = queue.Queue()
        threads = []

        for i in range(10):

            def worker():
                result = performance_worker(i)
                results.put(result)

            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for all workers
        for thread in threads:
            thread.join()

        # Check results
        successful_workers = 0
        while not results.empty():
            result = results.get()
            if "success" in result:
                successful_workers += 1

        self.assertEqual(successful_workers, 10)

    def test_memory_scalability(self):
        """Test memory usage scalability."""
        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())
        initial_memory = gc.get_stats()

        # Create many instances of various classes
        instances = []

        for i in range(100):
            # Create various objects
            config = ConfigManager()
            validator = CoordinateValidator()
            recovery = RecoveryManager()
            context = RetryContext(f"operation_{i}", max_retries=5)

            instances.extend([config, validator, recovery, context])

        # Force garbage collection
        gc.collect()
        after_objects = len(gc.get_objects())
        after_memory = gc.get_stats()

        # Memory usage should scale reasonably
        objects_created = after_objects - initial_objects
        self.assertLess(objects_created, 2000)  # Should not create excessive objects

        # Clean up
        del instances
        gc.collect()


class PerformanceRegressionTests(unittest.TestCase):
    """Test for performance regressions."""

    def test_configuration_performance_regression(self):
        """Test that configuration performance doesn't regress."""
        config = ConfigManager()

        # Establish baseline performance
        iterations = 1000
        start_time = time.time()

        for _ in range(iterations):
            config.get_setting("monkey_coords")
            config.update_setting("test_value", "test")

        baseline_time = time.time() - start_time

        # This test serves as a baseline for future regression testing
        # In practice, you'd compare against a stored baseline
        self.assertLess(baseline_time, 0.1)  # Should be fast

    def test_validation_performance_regression(self):
        """Test that validation performance doesn't regress."""
        validator = CoordinateValidator()

        # Establish baseline performance
        test_coords = [(x, y) for x in range(100) for y in range(100)]

        start_time = time.time()
        for coords in test_coords:
            validator.validate_coordinates(coords, "regression_test")
        baseline_time = time.time() - start_time

        # This test serves as a baseline for future regression testing
        self.assertLess(baseline_time, 0.1)  # Should be fast

    def test_logging_performance_regression(self):
        """Test that logging performance doesn't regress."""
        logger = get_logger("regression_test")

        # Establish baseline performance
        iterations = 1000
        start_time = time.time()

        for i in range(iterations):
            logger.info(
                f"Regression test message {i}",
                extra={"iteration": i, "data": {"test": "value"}},
            )

        baseline_time = time.time() - start_time

        # This test serves as a baseline for future regression testing
        self.assertLess(baseline_time, 0.5)  # Should be reasonable


if __name__ == "__main__":
    unittest.main()
