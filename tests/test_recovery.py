"""
Comprehensive tests for the BTD6 recovery system.

Tests error recovery mechanisms, recovery strategies, and recovery
context management without requiring the actual game or GUI interactions.
"""

import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock

# Add the btd6_auto module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "btd6_auto"))

from btd6_auto.recovery import RecoveryManager
from btd6_auto.exceptions import (
    BTD6AutomationError,
    TemplateNotFoundError,
    WindowNotFoundError,
    RetryExhaustedError,
)


class RecoveryStrategyTests(unittest.TestCase):
    """Test cases for RecoveryStrategy base class."""

    def test_recovery_strategy_creation(self):
        """Test RecoveryStrategy creation and initialization."""
        strategy = RecoveryStrategy("test_strategy", priority=5)

        self.assertEqual(strategy.name, "test_strategy")
        self.assertEqual(strategy.priority, 5)
        self.assertEqual(strategy.max_attempts, 3)  # Default value
        self.assertEqual(strategy.cooldown_period, 60)  # Default value

    def test_recovery_strategy_with_custom_params(self):
        """Test RecoveryStrategy with custom parameters."""
        strategy = RecoveryStrategy(
            name="custom_strategy", priority=10, max_attempts=5, cooldown_period=30
        )

        self.assertEqual(strategy.name, "custom_strategy")
        self.assertEqual(strategy.priority, 10)
        self.assertEqual(strategy.max_attempts, 5)
        self.assertEqual(strategy.cooldown_period, 30)

    def test_recovery_strategy_execution(self):
        """Test RecoveryStrategy execute method."""
        strategy = RecoveryStrategy("test_strategy")

        # Mock the _execute method
        with patch.object(strategy, "_execute") as mock_execute:
            mock_execute.return_value = True

            # RecoveryContext removed; test only strategy execution logic
            result = strategy.execute(None)

            self.assertTrue(result)
            mock_execute.assert_called_once_with(None)

    def test_recovery_strategy_execution_failure(self):
        """Test RecoveryStrategy execute method with failure."""
        strategy = RecoveryStrategy("failing_strategy")

        with patch.object(strategy, "_execute") as mock_execute:
            mock_execute.return_value = False

            # RecoveryContext removed; test only strategy execution logic
            result = strategy.execute(None)

            self.assertFalse(result)

    def test_recovery_strategy_priority_comparison(self):
        """Test RecoveryStrategy priority comparison."""
        low_priority = RecoveryStrategy("low", priority=1)
        high_priority = RecoveryStrategy("high", priority=10)
        medium_priority = RecoveryStrategy("medium", priority=5)

        strategies = [high_priority, low_priority, medium_priority]

        # Should sort by priority (highest first)
        sorted_strategies = sorted(strategies, reverse=True)
        self.assertEqual(sorted_strategies[0], high_priority)
        self.assertEqual(sorted_strategies[1], medium_priority)
        self.assertEqual(sorted_strategies[2], low_priority)


class RecoveryContextTests(unittest.TestCase):
    """Test cases for RecoveryContext class."""

    def test_recovery_context_creation(self):
        """Test RecoveryContext creation and initialization."""
        context = RecoveryContext("test_operation")

        self.assertEqual(context.operation, "test_operation")
        self.assertEqual(context.recovery_attempts, 0)
        self.assertEqual(len(context.attempt_history), 0)
        self.assertIsNone(context.last_recovery_time)
        self.assertFalse(context.recovery_in_progress)

    def test_recovery_context_attempt_tracking(self):
        """Test RecoveryContext attempt tracking."""
        context = RecoveryContext("test_operation")

        # Record a recovery attempt
        strategy = RecoveryStrategy("test_strategy")
        success = context.record_attempt(strategy, True, 0.5)

        self.assertTrue(success)
        self.assertEqual(context.recovery_attempts, 1)
        self.assertEqual(len(context.attempt_history), 1)

        # Check attempt details
        attempt = context.attempt_history[0]
        self.assertEqual(attempt["strategy_name"], "test_strategy")
        self.assertTrue(attempt["success"])
        self.assertEqual(attempt["duration"], 0.5)

    def test_recovery_context_failure_tracking(self):
        """Test RecoveryContext failure tracking."""
        context = RecoveryContext("test_operation")

        strategy = RecoveryStrategy("failing_strategy")
        success = context.record_attempt(strategy, False, 0.1)

        self.assertFalse(success)
        self.assertEqual(context.recovery_attempts, 1)

        attempt = context.attempt_history[0]
        self.assertFalse(attempt["success"])
        self.assertEqual(attempt["duration"], 0.1)

    def test_recovery_context_statistics(self):
        """Test RecoveryContext statistics calculation."""
        context = RecoveryContext("test_operation")

        # Record mixed success/failure attempts
        strategies = [
            RecoveryStrategy("strategy1"),
            RecoveryStrategy("strategy2"),
            RecoveryStrategy("strategy3"),
        ]

        context.record_attempt(strategies[0], True, 0.1)
        context.record_attempt(strategies[1], False, 0.2)
        context.record_attempt(strategies[2], True, 0.15)

        stats = context.get_statistics()

        self.assertEqual(stats["total_attempts"], 3)
        self.assertEqual(stats["successful_attempts"], 2)
        self.assertEqual(stats["failed_attempts"], 1)
        self.assertAlmostEqual(stats["success_rate"], 2 / 3, places=2)
        self.assertAlmostEqual(stats["average_duration"], 0.15, places=2)

    def test_recovery_context_cooldown_tracking(self):
        """Test RecoveryContext cooldown tracking."""
        context = RecoveryContext("test_operation")
        context.last_recovery_time = time.time()

        # Should be in cooldown if recently used
        self.assertTrue(context.is_in_cooldown(60))  # 60 second cooldown

        # Should not be in cooldown after time passes
        context.last_recovery_time = time.time() - 120  # 2 minutes ago
        self.assertFalse(context.is_in_cooldown(60))


class RecoveryManagerTests(unittest.TestCase):
    """Test cases for RecoveryManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.recovery_manager = RecoveryManager()

    def test_recovery_manager_initialization(self):
        """Test RecoveryManager initialization."""
        self.assertIsNotNone(self.recovery_manager.strategies)
        self.assertIsInstance(self.recovery_manager.strategies, dict)
        self.assertEqual(len(self.recovery_manager.strategies), 0)

    def test_register_strategy(self):
        """Test registering recovery strategies."""
        strategy1 = RecoveryStrategy("strategy1", priority=5)
        strategy2 = RecoveryStrategy("strategy2", priority=10)

        # Register strategies
        self.recovery_manager.register_strategy(strategy1)
        self.recovery_manager.register_strategy(strategy2)

        # Should be stored by name
        self.assertIn("strategy1", self.recovery_manager.strategies)
        self.assertIn("strategy2", self.recovery_manager.strategies)
        self.assertEqual(self.recovery_manager.strategies["strategy1"], strategy1)
        self.assertEqual(self.recovery_manager.strategies["strategy2"], strategy2)

    def test_register_duplicate_strategy(self):
        """Test registering duplicate strategy names."""
        strategy1 = RecoveryStrategy("duplicate", priority=5)
        strategy2 = RecoveryStrategy("duplicate", priority=10)

        # Register first strategy
        self.recovery_manager.register_strategy(strategy1)

        # Registering duplicate should overwrite
        self.recovery_manager.register_strategy(strategy2)

        self.assertEqual(self.recovery_manager.strategies["duplicate"], strategy2)
        self.assertEqual(self.recovery_manager.strategies["duplicate"].priority, 10)

    def test_get_available_strategies(self):
        """Test getting available strategies."""
        # No strategies registered
        available = self.recovery_manager.get_available_strategies()
        self.assertEqual(len(available), 0)

        # Register some strategies
        strategy1 = RecoveryStrategy("strategy1", priority=5)
        strategy2 = RecoveryStrategy("strategy2", priority=10)

        self.recovery_manager.register_strategy(strategy1)
        self.recovery_manager.register_strategy(strategy2)

        available = self.recovery_manager.get_available_strategies()
        self.assertEqual(len(available), 2)

        # Should be sorted by priority (highest first)
        self.assertEqual(available[0], strategy2)  # priority 10
        self.assertEqual(available[1], strategy1)  # priority 5

    def test_attempt_recovery_success(self):
        """Test successful recovery attempt."""
        # Create a mock strategy that succeeds
        strategy = RecoveryStrategy("success_strategy")
        strategy.execute = MagicMock(return_value=True)

        self.recovery_manager.register_strategy(strategy)

        context = RecoveryContext("test_operation")
        success = self.recovery_manager.attempt_recovery(context, "success_strategy")

        self.assertTrue(success)
        strategy.execute.assert_called_once_with(context)

    def test_attempt_recovery_failure(self):
        """Test failed recovery attempt."""
        # Create a mock strategy that fails
        strategy = RecoveryStrategy("failure_strategy")
        strategy.execute = MagicMock(return_value=False)

        self.recovery_manager.register_strategy(strategy)

        context = RecoveryContext("test_operation")
        success = self.recovery_manager.attempt_recovery(context, "failure_strategy")

        self.assertFalse(success)

    def test_attempt_recovery_with_nonexistent_strategy(self):
        """Test recovery attempt with non-existent strategy."""
        context = RecoveryContext("test_operation")

        with self.assertRaises(KeyError):
            self.recovery_manager.attempt_recovery(context, "nonexistent_strategy")

    def test_attempt_recovery_with_exception(self):
        """Test recovery attempt when strategy raises exception."""
        # Create a strategy that raises an exception
        strategy = RecoveryStrategy("exception_strategy")
        strategy.execute = MagicMock(side_effect=Exception("Strategy failed"))

        self.recovery_manager.register_strategy(strategy)

        context = RecoveryContext("test_operation")

        # Should handle the exception and return False
        success = self.recovery_manager.attempt_recovery(context, "exception_strategy")
        self.assertFalse(success)

    def test_attempt_all_available_strategies(self):
        """Test attempting all available recovery strategies."""
        # Create mix of successful and failing strategies
        success_strategy = RecoveryStrategy("success", priority=10)
        success_strategy.execute = MagicMock(return_value=True)

        fail_strategy = RecoveryStrategy("fail", priority=5)
        fail_strategy.execute = MagicMock(return_value=False)

        self.recovery_manager.register_strategy(success_strategy)
        self.recovery_manager.register_strategy(fail_strategy)

        context = RecoveryContext("test_operation")

        # Should try strategies in priority order and succeed with first one
        success = self.recovery_manager.attempt_all_strategies(context)

        self.assertTrue(success)
        success_strategy.execute.assert_called_once()
        fail_strategy.execute.assert_not_called()  # Should not try lower priority

    def test_attempt_all_strategies_all_fail(self):
        """Test attempting all strategies when all fail."""
        # Create failing strategies
        fail1 = RecoveryStrategy("fail1", priority=10)
        fail1.execute = MagicMock(return_value=False)

        fail2 = RecoveryStrategy("fail2", priority=5)
        fail2.execute = MagicMock(return_value=False)

        self.recovery_manager.register_strategy(fail1)
        self.recovery_manager.register_strategy(fail2)

        context = RecoveryContext("test_operation")

        # Should try all strategies and ultimately fail
        success = self.recovery_manager.attempt_all_strategies(context)

        self.assertFalse(success)
        fail1.execute.assert_called_once()
        fail2.execute.assert_called_once()


class ConcreteRecoveryStrategyTests(unittest.TestCase):
    """Test concrete implementations of recovery strategies."""

    def test_window_reactivation_strategy(self):
        """Test window reactivation recovery strategy."""

        # This would be a concrete strategy implementation
        class WindowReactivationStrategy(RecoveryStrategy):
            def __init__(self):
                super().__init__("window_reactivation", priority=10)

            def _execute(self, context):
                # Simulate window reactivation
                return True

        strategy = WindowReactivationStrategy()
        context = RecoveryContext("window_operation")

        result = strategy.execute(context)
        self.assertTrue(result)

    def test_coordinate_recalculation_strategy(self):
        """Test coordinate recalculation recovery strategy."""

        class CoordinateRecalculationStrategy(RecoveryStrategy):
            def __init__(self):
                super().__init__("coordinate_recalculation", priority=8)

            def _execute(self, context):
                # Simulate coordinate recalculation
                return True

        strategy = CoordinateRecalculationStrategy()
        context = RecoveryContext("coordinate_operation")

        result = strategy.execute(context)
        self.assertTrue(result)

    def test_template_refresh_strategy(self):
        """Test template refresh recovery strategy."""

        class TemplateRefreshStrategy(RecoveryStrategy):
            def __init__(self):
                super().__init__("template_refresh", priority=6)

            def _execute(self, context):
                # Simulate template refresh
                return False  # Sometimes fails

        strategy = TemplateRefreshStrategy()
        context = RecoveryContext("template_operation")

        result = strategy.execute(context)
        self.assertFalse(result)


class RecoveryIntegrationTests(unittest.TestCase):
    """Integration tests for recovery system with other components."""

    def test_recovery_with_exception_integration(self):
        """Test recovery system integration with exception handling."""
        recovery_manager = RecoveryManager()

        # Create strategy that handles specific exceptions
        class ExceptionHandlingStrategy(RecoveryStrategy):
            def __init__(self):
                super().__init__("exception_handler", priority=10)

            def _execute(self, context):
                # Check if context has exception information
                if hasattr(context, "original_exception"):
                    if isinstance(context.original_exception, TemplateNotFoundError):
                        return True  # Can handle this
                return False

        recovery_manager.register_strategy(ExceptionHandlingStrategy())

        # Test with exception context
        context = RecoveryContext("template_operation")
        context.original_exception = TemplateNotFoundError("test.png", operation="test")

        success = recovery_manager.attempt_recovery(context, "exception_handler")
        self.assertTrue(success)

    def test_recovery_with_logging_integration(self):
        """Test recovery system integration with logging."""
        with patch("btd6_auto.recovery.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            recovery_manager = RecoveryManager()

            strategy = RecoveryStrategy("logged_strategy")
            strategy.execute = MagicMock(return_value=True)

            recovery_manager.register_strategy(strategy)

            context = RecoveryContext("logged_operation")

            success = recovery_manager.attempt_recovery(context, "logged_strategy")

            self.assertTrue(success)
            # Logger should have been used for recovery operations

    def test_recovery_with_validation_integration(self):
        """Test recovery system integration with validation."""
        from btd6_auto.validation import CoordinateValidator

        recovery_manager = RecoveryManager()
        validator = CoordinateValidator()

        class ValidationRecoveryStrategy(RecoveryStrategy):
            def __init__(self):
                super().__init__("validation_recovery", priority=7)

            def _execute(self, context):
                # Simulate validating and fixing coordinates
                try:
                    validator.validate_coordinates((100, 100), "recovery_test")
                    return True
                except Exception:
                    return False

        recovery_manager.register_strategy(ValidationRecoveryStrategy())

        context = RecoveryContext("validation_operation")
        success = recovery_manager.attempt_recovery(context, "validation_recovery")

        self.assertTrue(success)


class RecoveryPerformanceTests(unittest.TestCase):
    """Test recovery system performance characteristics."""

    def test_recovery_strategy_execution_performance(self):
        """Test recovery strategy execution performance."""
        strategy = RecoveryStrategy("performance_test")

        # Mock fast execution
        strategy._execute = MagicMock(return_value=True)

        context = RecoveryContext("test_operation")

        # Time multiple executions
        iterations = 100
        start_time = time.time()

        for _ in range(iterations):
            strategy.execute(context)

        total_time = time.time() - start_time

        # Should be reasonably fast
        avg_time = total_time / iterations
        self.assertLess(avg_time, 0.01)  # Less than 10ms per execution

    def test_recovery_manager_overhead(self):
        """Test RecoveryManager overhead."""
        recovery_manager = RecoveryManager()

        # Register many strategies
        strategies = []
        for i in range(50):
            strategy = RecoveryStrategy(f"strategy_{i}", priority=i)
            strategies.append(strategy)
            recovery_manager.register_strategy(strategy)

        # Time getting available strategies
        start_time = time.time()
        for _ in range(100):
            available = recovery_manager.get_available_strategies()
            self.assertEqual(len(available), 50)
        total_time = time.time() - start_time

        # Should be reasonably fast to sort and return strategies
        self.assertLess(total_time, 0.1)  # Less than 100ms for 100 operations

    def test_recovery_context_memory_usage(self):
        """Test RecoveryContext memory usage."""
        import gc

        # Create many recovery contexts
        contexts = []
        for i in range(100):
            context = RecoveryContext(f"operation_{i}")
            # Add some attempt history
            for j in range(10):
                strategy = RecoveryStrategy(f"strategy_{j}")
                context.record_attempt(strategy, j % 2 == 0, 0.1)
            contexts.append(context)

        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Delete contexts
        del contexts
        gc.collect()
        final_objects = len(gc.get_objects())

        # Memory should be cleaned up properly
        objects_created = final_objects - initial_objects
        self.assertLess(objects_created, 100)  # Should not leak excessive objects


class RecoveryEdgeCasesTests(unittest.TestCase):
    """Test edge cases and error conditions for recovery system."""

    def test_recovery_with_empty_strategy_list(self):
        """Test recovery with no registered strategies."""
        recovery_manager = RecoveryManager()
        context = RecoveryContext("test_operation")

        # Should handle gracefully
        available = recovery_manager.get_available_strategies()
        self.assertEqual(len(available), 0)

        # Should return False when no strategies available
        success = recovery_manager.attempt_all_strategies(context)
        self.assertFalse(success)

    def test_recovery_strategy_with_long_names(self):
        """Test recovery strategies with very long names."""
        long_name = "a" * 1000  # Very long strategy name
        strategy = RecoveryStrategy(long_name, priority=5)

        recovery_manager = RecoveryManager()
        recovery_manager.register_strategy(strategy)

        # Should handle long names without issues
        available = recovery_manager.get_available_strategies()
        self.assertEqual(len(available), 1)
        self.assertEqual(available[0].name, long_name)

    def test_recovery_context_with_many_attempts(self):
        """Test RecoveryContext with many recorded attempts."""
        context = RecoveryContext("test_operation")

        # Record many attempts
        for i in range(1000):
            strategy = RecoveryStrategy(f"strategy_{i % 10}")
            success = i % 3 == 0  # 1/3 success rate
            context.record_attempt(strategy, success, 0.01)

        # Should handle large number of attempts
        self.assertEqual(context.recovery_attempts, 1000)
        self.assertEqual(len(context.attempt_history), 1000)

        # Statistics should still work
        stats = context.get_statistics()
        self.assertEqual(stats["total_attempts"], 1000)
        self.assertAlmostEqual(stats["success_rate"], 1 / 3, places=1)

    def test_concurrent_recovery_operations(self):
        """Test concurrent recovery operations."""
        import threading
        import queue

        recovery_manager = RecoveryManager()
        results = queue.Queue()

        def concurrent_recovery(operation_id):
            try:
                strategy = RecoveryStrategy(f"concurrent_strategy_{operation_id}")
                strategy.execute = MagicMock(return_value=True)

                recovery_manager.register_strategy(strategy)

                context = RecoveryContext(f"operation_{operation_id}")

                success = recovery_manager.attempt_recovery(context, strategy.name)
                results.put((operation_id, success))

            except Exception as e:
                results.put((operation_id, f"error: {e}"))

        # Start multiple concurrent recovery operations
        threads = []
        for i in range(10):
            thread = threading.Thread(target=concurrent_recovery, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check results
        successful_operations = 0
        while not results.empty():
            operation_id, result = results.get()
            if result is True:
                successful_operations += 1

        self.assertEqual(successful_operations, 10)


if __name__ == "__main__":
    unittest.main()
