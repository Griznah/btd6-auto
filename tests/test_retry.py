"""
Comprehensive tests for the BTD6 retry mechanism.

Tests retry decorators, backoff strategies, exception filtering, and retry
context management without requiring the actual game or GUI interactions.
"""

import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock

# Add the btd6_auto module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "btd6_auto"))

from btd6_auto.retry_utils import retry, RetryContext, RetryExhaustedError
from btd6_auto.exceptions import (
    TemplateNotFoundError,
    MatchFailedError,
    WindowActivationError,
    InvalidCoordinateError,
)


class RetryDecoratorTests(unittest.TestCase):
    """Test cases for the @retry decorator."""

    def test_retry_success_on_first_attempt(self):
        """Test retry decorator with immediate success."""
        attempt_count = 0

        @retry(max_retries=3, base_delay=0.01)
        def successful_operation():
            nonlocal attempt_count
            attempt_count += 1
            return "success"

        result = successful_operation()

        self.assertEqual(result, "success")
        self.assertEqual(attempt_count, 1)  # Should only run once

    def test_retry_success_after_failures(self):
        """Test retry decorator that succeeds after some failures."""
        attempt_count = 0

        @retry(max_retries=5, base_delay=0.01)
        def eventually_successful_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise TemplateNotFoundError("template.png", operation="test")
            return "success"

        result = eventually_successful_operation()

        self.assertEqual(result, "success")
        self.assertEqual(attempt_count, 3)  # Should retry until success

    def test_retry_exhaustion(self):
        """Test retry decorator when all retries are exhausted."""

        @retry(max_retries=2, base_delay=0.01)
        def always_failing_operation():
            raise MatchFailedError("template.png", operation="test")

        with self.assertRaises(RetryExhaustedError) as cm:
            always_failing_operation()

        error = cm.exception
        self.assertEqual(error.operation, "test")
        self.assertEqual(error.max_retries, 2)
        self.assertIsInstance(error.final_exception, MatchFailedError)

    def test_retry_with_different_exceptions(self):
        """Test retry behavior with different exception types."""
        attempt_count = 0

        @retry(
            max_retries=3, base_delay=0.01, retryable_exceptions=[TemplateNotFoundError]
        )
        def selective_retry_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise TemplateNotFoundError(
                    "template.png", operation="test"
                )  # Should retry
            elif attempt_count == 2:
                raise InvalidCoordinateError(
                    (100, 200), operation="test"
                )  # Should not retry
            return "success"

        # Should raise the non-retryable exception
        with self.assertRaises(InvalidCoordinateError):
            selective_retry_operation()

        self.assertEqual(
            attempt_count, 2
        )  # Should not retry the non-retryable exception

    def test_retry_with_backoff(self):
        """Test retry with exponential backoff."""
        attempt_count = 0
        start_time = time.time()

        @retry(max_retries=3, base_delay=0.1, backoff_factor=2.0)
        def backoff_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise WindowActivationError("BloonsTD6", operation="test")
            return "success"

        with patch("time.sleep") as mock_sleep:
            result = backoff_operation()

        self.assertEqual(result, "success")
        self.assertEqual(attempt_count, 3)

        # Should have called sleep with increasing delays
        sleep_calls = mock_sleep.call_args_list
        self.assertEqual(len(sleep_calls), 2)  # Two delays for three attempts

        # Check that delays are increasing (approximately exponential backoff)
        first_delay = sleep_calls[0][0][0]
        second_delay = sleep_calls[1][0][0]
        self.assertGreater(second_delay, first_delay)

    def test_retry_with_jitter(self):
        """Test retry with jitter to avoid thundering herd."""

        @retry(max_retries=3, base_delay=0.1, jitter=True)
        def jitter_operation():
            raise TemplateNotFoundError("template.png", operation="test")

        with patch("time.sleep") as mock_sleep:
            with self.assertRaises(RetryExhaustedError):
                jitter_operation()

        # Should have sleep calls with jitter
        sleep_calls = mock_sleep.call_args_list
        delays = [call[0][0] for call in sleep_calls]

        # All delays should be around the base delay but with some variation
        for delay in delays:
            self.assertGreater(delay, 0.05)  # Should be at least half of base delay
            self.assertLess(delay, 0.2)  # Should be at most 1.5x base delay

    def test_retry_max_retries_zero(self):
        """Test retry with max_retries=0 (no retries)."""
        attempt_count = 0

        @retry(max_retries=0, base_delay=0.01)
        def no_retry_operation():
            nonlocal attempt_count
            attempt_count += 1
            raise TemplateNotFoundError("template.png", operation="test")

        with self.assertRaises(TemplateNotFoundError):
            no_retry_operation()

        self.assertEqual(attempt_count, 1)  # Should not retry

    def test_retry_with_custom_exception_filter(self):
        """Test retry with custom exception filtering function."""
        attempt_count = 0

        def custom_exception_filter(exception):
            # Only retry on specific error messages
            return "retry_me" in str(exception)

        @retry(
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=[ValueError],
            exception_filter=custom_exception_filter,
        )
        def custom_filter_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise ValueError("retry_me")  # Should retry
            elif attempt_count == 2:
                raise ValueError("dont_retry")  # Should not retry
            return "success"

        # Should raise the non-retryable exception
        with self.assertRaises(ValueError) as cm:
            custom_filter_operation()

        self.assertEqual(str(cm.exception), "dont_retry")
        self.assertEqual(attempt_count, 2)

    def test_retry_preserves_original_exception(self):
        """Test that retry preserves the original exception information."""
        original_error = TemplateNotFoundError(
            "original.png", operation="original_test"
        )

        @retry(max_retries=2, base_delay=0.01)
        def preserve_exception_operation():
            raise original_error

        with self.assertRaises(RetryExhaustedError) as cm:
            preserve_exception_operation()

        retry_error = cm.exception
        self.assertEqual(retry_error.final_exception, original_error)
        self.assertEqual(retry_error.final_exception.template_path, "original.png")


class RetryContextTests(unittest.TestCase):
    """Test cases for RetryContext class."""

    def test_retry_context_creation(self):
        """Test RetryContext creation and initialization."""
        context = RetryContext("test_operation", max_retries=3)

        self.assertEqual(context.operation, "test_operation")
        self.assertEqual(context.max_retries, 3)
        self.assertEqual(context.current_attempt, 0)
        self.assertEqual(len(context.attempts), 0)

    def test_retry_context_attempt_tracking(self):
        """Test RetryContext attempt tracking."""
        context = RetryContext("test_operation", max_retries=3)

        # Record attempts
        context.record_attempt(
            1, 0.1, TemplateNotFoundError("test.png", operation="test")
        )
        context.record_attempt(2, 0.2, MatchFailedError("test.png", operation="test"))

        self.assertEqual(context.current_attempt, 2)
        self.assertEqual(len(context.attempts), 2)

        # Check attempt details
        first_attempt = context.attempts[0]
        self.assertEqual(first_attempt["attempt_number"], 1)
        self.assertEqual(first_attempt["duration"], 0.1)
        self.assertIsInstance(first_attempt["exception"], TemplateNotFoundError)

    def test_retry_context_success_tracking(self):
        """Test RetryContext success tracking."""
        context = RetryContext("test_operation", max_retries=3)

        # Record a successful attempt
        context.record_success(2, 0.15)

        self.assertTrue(context.success)
        self.assertEqual(context.total_attempts, 2)
        self.assertEqual(context.total_time, 0.15)

    def test_retry_context_exhaustion(self):
        """Test RetryContext when retries are exhausted."""
        context = RetryContext("test_operation", max_retries=2)

        # Exhaust retries
        context.record_attempt(
            1, 0.1, TemplateNotFoundError("test.png", operation="test")
        )
        context.record_attempt(2, 0.2, MatchFailedError("test.png", operation="test"))

        # Should be exhausted
        self.assertTrue(context.is_exhausted())
        self.assertEqual(context.current_attempt, 2)

    def test_retry_context_statistics(self):
        """Test RetryContext statistics calculation."""
        context = RetryContext("test_operation", max_retries=3)

        # Record multiple attempts with different durations
        context.record_attempt(
            1, 0.1, TemplateNotFoundError("test.png", operation="test")
        )
        context.record_success(2, 0.15)
        context.record_attempt(3, 0.05, MatchFailedError("test.png", operation="test"))

        stats = context.get_statistics()

        self.assertEqual(stats["total_attempts"], 3)
        self.assertEqual(stats["successful_attempts"], 1)
        self.assertEqual(stats["failed_attempts"], 2)
        self.assertAlmostEqual(stats["total_time"], 0.3, places=1)
        self.assertAlmostEqual(stats["average_time_per_attempt"], 0.1, places=1)


class RetryIntegrationTests(unittest.TestCase):
    """Integration tests for retry mechanism with other systems."""

    def test_retry_with_logging_integration(self):
        """Test retry mechanism integration with logging."""
        with patch("btd6_auto.retry_utils.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            attempt_count = 0

            @retry(max_retries=2, base_delay=0.01)
            def logged_operation():
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 2:
                    raise TemplateNotFoundError("test.png", operation="logged_test")
                return "success"

            with patch("time.sleep"):
                result = logged_operation()

            self.assertEqual(result, "success")
            # Logger should have been called for retry operations
            self.assertGreater(mock_logger.info.call_count, 0)

    def test_retry_with_validation_integration(self):
        """Test retry mechanism integration with validation."""
        from btd6_auto.validation import CoordinateValidator

        validator = CoordinateValidator()
        attempt_count = 0

        @retry(max_retries=3, base_delay=0.01, retryable_exceptions=[ValueError])
        def validated_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                # First attempt: invalid coordinates (should retry due to ValueError)
                try:
                    validator.validate_coordinates((-100, -100), "test")
                except Exception as e:
                    raise ValueError(f"Validation failed: {e}")
            return "success"

        with patch("time.sleep"):
            result = validated_operation()

        self.assertEqual(result, "success")
        self.assertEqual(attempt_count, 2)  # Should retry once

    def test_retry_with_exception_context(self):
        """Test retry mechanism with exception context preservation."""

        @retry(max_retries=2, base_delay=0.01)
        def contextual_operation():
            raise MatchFailedError(
                "context_test.png",
                operation="context_test",
                details={"match_score": 0.5, "threshold": 0.8},
            )

        with self.assertRaises(RetryExhaustedError) as cm:
            contextual_operation()

        retry_error = cm.exception
        final_exception = retry_error.final_exception

        # Original exception context should be preserved
        self.assertEqual(final_exception.operation, "context_test")
        self.assertEqual(final_exception.details["match_score"], 0.5)
        self.assertEqual(final_exception.details["threshold"], 0.8)


class RetryPerformanceTests(unittest.TestCase):
    """Test retry mechanism performance characteristics."""

    def test_retry_overhead_measurement(self):
        """Test measuring retry mechanism overhead."""

        def simple_operation():
            return "success"

        def failing_operation():
            raise TemplateNotFoundError("test.png", operation="test")

        # Time operation without retry
        iterations = 100
        start_time = time.time()
        for _ in range(iterations):
            simple_operation()
        no_retry_time = time.time() - start_time

        # Time operation with retry (but no failures)
        start_time = time.time()
        for _ in range(iterations):

            @retry(max_retries=3, base_delay=0.001)
            def retried_operation():
                return simple_operation()

            retried_operation()
        with_retry_time = time.time() - start_time

        # Retry should add minimal overhead for successful operations
        overhead_ratio = with_retry_time / no_retry_time
        self.assertGreater(overhead_ratio, 1.0)
        self.assertLess(overhead_ratio, 3.0)  # Reasonable overhead

    def test_retry_timing_accuracy(self):
        """Test retry timing accuracy."""

        @retry(max_retries=2, base_delay=0.05)
        def timed_operation():
            raise TemplateNotFoundError("test.png", operation="timing_test")

        with patch("time.sleep") as mock_sleep:
            start_time = time.time()
            with self.assertRaises(RetryExhaustedError):
                timed_operation()
            end_time = time.time()

        # Should have called sleep with base delay
        sleep_calls = mock_sleep.call_args_list
        self.assertEqual(len(sleep_calls), 1)
        self.assertAlmostEqual(sleep_calls[0][0][0], 0.05, places=1)

    def test_retry_memory_usage(self):
        """Test retry mechanism memory usage."""
        import gc

        # Force garbage collection to get baseline
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Create many retry contexts
        contexts = []
        for i in range(100):
            context = RetryContext(f"test_operation_{i}", max_retries=3)
            contexts.append(context)

        # Force garbage collection again
        gc.collect()
        after_objects = len(gc.get_objects())

        # Memory usage should be reasonable (not growing excessively)
        object_increase = after_objects - initial_objects
        self.assertLess(object_increase, 1000)  # Should not create too many objects

        # Clean up
        del contexts
        gc.collect()


class RetryEdgeCasesTests(unittest.TestCase):
    """Test edge cases and error conditions for retry mechanism."""

    def test_retry_with_very_short_delays(self):
        """Test retry with very short delays."""
        attempt_count = 0

        @retry(max_retries=3, base_delay=0.001)  # 1ms delay
        def fast_retry_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise TemplateNotFoundError("test.png", operation="fast_test")
            return "success"

        start_time = time.time()
        result = fast_retry_operation()
        end_time = time.time()

        self.assertEqual(result, "success")
        self.assertEqual(attempt_count, 3)

        # Should complete quickly due to short delays
        total_time = end_time - start_time
        self.assertLess(total_time, 0.1)  # Should complete in less than 100ms

    def test_retry_with_very_long_delays(self):
        """Test retry with very long delays."""

        @retry(max_retries=2, base_delay=1.0)  # 1 second delay
        def slow_retry_operation():
            raise TemplateNotFoundError("test.png", operation="slow_test")

        with patch("time.sleep") as mock_sleep:
            start_time = time.time()
            with self.assertRaises(RetryExhaustedError):
                slow_retry_operation()
            end_time = time.time()

        # Should have called sleep with long delay
        sleep_calls = mock_sleep.call_args_list
        self.assertEqual(len(sleep_calls), 1)
        self.assertEqual(sleep_calls[0][0][0], 1.0)

    def test_retry_with_nested_retries(self):
        """Test nested retry decorators."""
        outer_attempts = 0
        inner_attempts = 0

        @retry(max_retries=2, base_delay=0.01)
        def outer_operation():
            nonlocal outer_attempts
            outer_attempts += 1

            @retry(max_retries=2, base_delay=0.01)
            def inner_operation():
                nonlocal inner_attempts
                inner_attempts += 1
                if inner_attempts < 2:
                    raise TemplateNotFoundError("test.png", operation="inner")
                return "inner_success"

            return inner_operation()

        with patch("time.sleep"):
            result = outer_operation()

        self.assertEqual(result, "inner_success")
        # Both should have retried
        self.assertGreater(outer_attempts, 1)
        self.assertGreater(inner_attempts, 1)

    def test_retry_with_concurrent_operations(self):
        """Test retry mechanism with concurrent operations."""
        import threading
        import queue

        results = queue.Queue()
        errors = queue.Queue()

        def concurrent_operation(operation_id):
            try:
                attempt_count = 0

                @retry(max_retries=3, base_delay=0.01)
                def failing_operation():
                    nonlocal attempt_count
                    attempt_count += 1
                    if attempt_count < 2:
                        raise MatchFailedError("test.png", operation="concurrent_test")
                    return f"success_{operation_id}"

                with patch("time.sleep"):
                    result = failing_operation()
                    results.put((operation_id, result))

            except Exception as e:
                errors.put((operation_id, e))

        # Start multiple concurrent operations
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check results
        successful_results = []
        while not results.empty():
            successful_results.append(results.get())

        while not errors.empty():
            errors.get()  # Should be no errors

        self.assertEqual(len(successful_results), 5)
        for operation_id, result in successful_results:
            self.assertEqual(result, f"success_{operation_id}")


if __name__ == "__main__":
    unittest.main()
