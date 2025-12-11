"""
Tests for the DebugManager class and debug functionality.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch
import time

from btd6_auto.debug_manager import DebugManager, DebugLevel, PerformanceTracker


class TestDebugManager:
    """Test cases for DebugManager class."""

    def test_debug_manager_initialization(self):
        """Test DebugManager initialization with different configs."""
        # Test default config
        manager = DebugManager({})
        assert not manager.enabled
        assert manager.level == DebugLevel.BASIC
        assert manager.log_to_file
        assert manager.log_to_console

        # Test custom config
        config = {
            "enabled": True,
            "level": 2,  # DETAILED
            "log_to_console": False,
            "performance_tracking": False
        }
        manager = DebugManager(config)
        assert manager.enabled
        assert manager.level == DebugLevel.DETAILED
        assert not manager.log_to_console
        assert not manager.performance_tracking

    def test_debug_levels(self):
        """Test debug level functionality."""
        config = {"enabled": True, "level": 0}  # NONE
        manager = DebugManager(config)

        # Should not log when level is NONE
        with patch('logging.getLogger') as mock_logger:
            manager.log_basic("Test", "This should not log")
            mock_logger.return_value.info.assert_not_called()

        # Test different levels
        for level_value in range(4):  # 0-3
            config = {"enabled": True, "level": level_value}
            manager = DebugManager(config)
            expected_level = DebugLevel(level_value)
            assert manager.level == expected_level

    def test_performance_tracker(self):
        """Test PerformanceTracker functionality."""
        tracker = PerformanceTracker("test_operation")

        # Test starting and finishing
        tracker.start()
        time.sleep(0.01)  # Small delay
        duration = tracker.finish()

        assert duration > 0
        assert duration < 1.0  # Should be less than 1 second

        # Test checkpoints
        tracker = PerformanceTracker("test_operation")
        tracker.start()
        tracker.checkpoint("checkpoint1")
        tracker.checkpoint("checkpoint2")
        duration = tracker.finish()

        assert len(tracker.checkpoints) == 2
        assert tracker.checkpoints[0]["name"] == "checkpoint1"
        assert tracker.checkpoints[1]["name"] == "checkpoint2"

        # Test finish without start
        tracker = PerformanceTracker("test_operation")
        duration = tracker.finish()
        assert duration == 0.0

    def test_performance_tracking_integration(self):
        """Test performance tracking integration in DebugManager."""
        config = {"enabled": True, "performance_tracking": True}
        manager = DebugManager(config)

        # Start and finish tracking
        operation_id = manager.start_performance_tracking("test_operation")
        assert operation_id is not None
        assert operation_id in manager.active_operations

        # Add checkpoint
        manager.add_checkpoint(operation_id, "test_checkpoint")
        tracker = manager.active_operations[operation_id]
        assert len(tracker.checkpoints) == 1
        assert tracker.checkpoints[0]["name"] == "test_checkpoint"

        # Small delay to ensure duration > 0
        time.sleep(0.001)

        # Finish tracking
        duration = manager.finish_performance_tracking(operation_id)
        assert duration > 0
        assert operation_id not in manager.active_operations

        # Check that performance data was stored
        assert "test_operation" in manager.performance_data
        assert len(manager.performance_data["test_operation"]) == 1
        assert manager.performance_data["test_operation"][0] == duration

    def test_performance_tracking_disabled(self):
        """Test performance tracking when disabled."""
        config = {"enabled": True, "performance_tracking": False}
        manager = DebugManager(config)

        # Should return None when tracking is disabled
        operation_id = manager.start_performance_tracking("test_operation")
        assert operation_id is None

        duration = manager.finish_performance_tracking("test_operation")
        assert duration is None

    def test_logging_methods(self):
        """Test different logging methods."""
        config = {"enabled": True, "level": 3}  # VERBOSE
        manager = DebugManager(config)

        with patch('logging.getLogger') as mock_logger:
            logger_instance = Mock()
            mock_logger.return_value = logger_instance

            # Test basic logging
            manager.log_basic("TestComponent", "Basic message", "info")
            logger_instance.info.assert_called_with("Basic message")

            # Test detailed logging with kwargs
            manager.log_detailed("TestComponent", "Detailed message", key1="value1", key2="value2")
            expected_detailed = "Detailed message | key1=value1 | key2=value2"
            logger_instance.info.assert_called_with(expected_detailed)

            # Test verbose logging with data
            test_data = {"key": "value", "number": 42}
            manager.log_verbose("TestComponent", "Verbose message", data=test_data)
            expected_verbose = "Verbose message\nData: " + json.dumps(test_data, indent=2, default=str)
            logger_instance.debug.assert_called_with(expected_verbose)

    def test_error_logging(self):
        """Test error logging functionality."""
        config = {"enabled": True}
        manager = DebugManager(config)

        test_exception = ValueError("Test error message")
        test_context = {"key": "value", "attempt": 3}

        with patch('logging.getLogger') as mock_logger:
            logger_instance = Mock()
            mock_logger.return_value = logger_instance

            manager.log_error("TestComponent", test_exception, context=test_context)

            # Check that error was logged
            logger_instance.error.assert_called()
            logger_instance.debug.assert_called()

            # Check error history
            assert len(manager.error_history) == 1
            error_entry = manager.error_history[0]
            assert error_entry["component"] == "TestComponent"
            assert error_entry["error_type"] == "ValueError"
            assert error_entry["error_message"] == "Test error message"
            assert error_entry["context"] == test_context

    def test_vision_logging(self):
        """Test vision result logging."""
        config = {"enabled": True, "level": DebugLevel.DETAILED.value}
        manager = DebugManager(config)

        with patch.object(manager, 'get_logger') as mock_get_logger:
            logger_instance = Mock()
            mock_get_logger.return_value = logger_instance

            # Test successful vision result
            manager.log_vision_result("test_operation", True, confidence=0.85,
                                    match_info={"location": (100, 200)},
                                    processing_time=0.123)

            # Should log success
            logger_instance.info.assert_called()

            # Test failed vision result
            manager.log_vision_result("test_operation", False, confidence=0.45,
                                    match_info={"location": None})

            # Should log failure
            assert logger_instance.info.call_count >= 1

    def test_action_logging(self):
        """Test action logging."""
        config = {"enabled": True, "level": DebugLevel.DETAILED.value}
        manager = DebugManager(config)

        with patch.object(manager, 'get_logger') as mock_get_logger:
            logger_instance = Mock()
            mock_get_logger.return_value = logger_instance

            # Test successful action
            manager.log_action("place_monkey", "Dart Monkey", True,
                             details={"position": (100, 200), "cost": 200})

            # Should log success
            logger_instance.info.assert_called()

            # Test failed action
            manager.log_action("place_monkey", "Dart Monkey", False,
                             details={"position": (100, 200)})

            # Should log failure
            assert logger_instance.info.call_count >= 1

    def test_performance_stats(self):
        """Test performance statistics."""
        config = {"enabled": True, "performance_tracking": True}
        manager = DebugManager(config)

        # Add some performance data
        operation_id = manager.start_performance_tracking("test_operation")
        time.sleep(0.01)
        manager.finish_performance_tracking(operation_id)

        operation_id2 = manager.start_performance_tracking("test_operation")
        time.sleep(0.02)
        manager.finish_performance_tracking(operation_id2)

        operation_id3 = manager.start_performance_tracking("another_operation")
        time.sleep(0.03)
        manager.finish_performance_tracking(operation_id3)

        # Get stats
        stats = manager.get_performance_stats()

        assert "test_operation" in stats
        assert "another_operation" in stats

        test_op_stats = stats["test_operation"]
        assert test_op_stats["count"] == 2
        assert test_op_stats["total_time"] > 0
        assert test_op_stats["average_time"] > 0
        assert test_op_stats["min_time"] <= test_op_stats["average_time"] <= test_op_stats["max_time"]

        another_op_stats = stats["another_operation"]
        assert another_op_stats["count"] == 1
        assert another_op_stats["total_time"] == another_op_stats["average_time"]

    def test_clear_performance_data(self):
        """Test clearing performance data."""
        config = {"enabled": True, "performance_tracking": True}
        manager = DebugManager(config)

        # Add some data
        operation_id = manager.start_performance_tracking("test_operation")
        manager.finish_performance_tracking(operation_id)

        assert len(manager.performance_data) > 0

        # Clear data
        manager.clear_performance_data()
        assert len(manager.performance_data) == 0

    def test_log_performance_summary(self):
        """Test performance summary logging."""
        config = {"enabled": True, "performance_tracking": True}
        manager = DebugManager(config)

        with patch.object(manager, 'get_logger') as mock_get_logger:
            logger_instance = Mock()
            mock_get_logger.return_value = logger_instance

            # Test with no data
            manager.log_performance_summary()
            logger_instance.info.assert_called_with("No performance data available")

            # Add some data and test
            operation_id = manager.start_performance_tracking("test_operation")
            time.sleep(0.001)  # Small delay to ensure duration > 0
            manager.finish_performance_tracking(operation_id)

            manager.log_performance_summary()
            # Should have called info multiple times (header + operation line)
            assert logger_instance.info.call_count >= 3

    def test_error_history_limit(self):
        """Test that error history doesn't grow indefinitely."""
        config = {"enabled": True}
        manager = DebugManager(config)

        test_exception = ValueError("Test error")

        # Add more than 100 errors
        for i in range(110):
            manager.log_error("TestComponent", test_exception, context={"iteration": i})

        # Should be limited to 100
        assert len(manager.error_history) == 100

        # Should keep the most recent 100
        assert manager.error_history[-1]["context"]["iteration"] == 109
        assert manager.error_history[0]["context"]["iteration"] == 10


class TestDebugIntegration:
    """Test integration of debug functionality with other components."""

    def test_debug_level_enum(self):
        """Test DebugLevel enum values."""
        assert DebugLevel.NONE.value == 0
        assert DebugLevel.BASIC.value == 1
        assert DebugLevel.DETAILED.value == 2
        assert DebugLevel.VERBOSE.value == 3

    @patch('btd6_auto.debug_manager.logging')
    def test_log_file_creation(self, mock_logging):
        """Test that log files are created when log_to_file is True."""
        config = {
            "enabled": True,
            "log_to_file": True,
            "log_to_console": False
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Create manager to trigger logs directory creation
                _ = DebugManager(config)

                # Check that file handler was configured
                mock_logging.FileHandler.assert_called()

                # Should have created a logs directory
                logs_dir = Path(temp_dir) / "logs"
                assert logs_dir.exists()

            finally:
                os.chdir(original_cwd)

    def test_disabled_debug_manager(self):
        """Test that disabled debug manager doesn't log."""
        config = {"enabled": False}
        manager = DebugManager(config)

        with patch('logging.getLogger') as mock_logger:
            logger_instance = Mock()
            mock_logger.return_value = logger_instance

            # All logging methods should not call logging
            manager.log_basic("Test", "message")
            manager.log_detailed("Test", "message")
            manager.log_verbose("Test", "message", data={})
            manager.log_error("Test", Exception("test"))
            manager.log_vision_result("test", True)
            manager.log_action("test", "target", True)

            logger_instance.info.assert_not_called()
            logger_instance.debug.assert_not_called()
            logger_instance.error.assert_not_called()

        # Performance tracking should also not work
        operation_id = manager.start_performance_tracking("test")
        assert operation_id is None

        duration = manager.finish_performance_tracking("test")
        assert duration is None


if __name__ == "__main__":
    pytest.main([__file__])