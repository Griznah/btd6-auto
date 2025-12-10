"""
Test to reproduce and verify DXGI errors in debug mode.
This test helps identify the issue with BetterCam when debug mode is enabled.
"""

import pytest
import logging
import time
from unittest.mock import Mock, patch, MagicMock
from btd6_auto.debug_manager import DebugManager
from btd6_auto.vision import capture_region, _CAMERA, _CAPTURE_RETRIES


class TestDebugModeDXGI:
    """Test DXGI errors in debug mode."""

    def test_debug_manager_initialization(self):
        """Test that debug manager initializes correctly with different levels."""
        # Test with debug disabled
        config = {
            "enabled": False,
            "level": 1
        }
        debug_manager = DebugManager(config)
        assert not debug_manager.enabled
        assert debug_manager.level.value == 1

        # Test with debug enabled at verbose level
        config = {
            "enabled": True,
            "level": 3,  # VERBOSE
            "log_to_file": False,  # Disable file logging for tests
            "log_to_console": False
        }
        debug_manager = DebugManager(config)
        assert debug_manager.enabled
        assert debug_manager.level.value == 3

    @patch('btd6_auto.vision._CAMERA')
    @patch('btd6_auto.vision._DEBUG_MANAGER')
    def test_capture_region_with_debug_logging(self, mock_debug_manager, mock_camera):
        """Test capture_region behavior with debug logging enabled."""
        # Setup mock debug manager
        mock_debug_manager.enabled = True
        mock_debug_manager.level.value = 3  # VERBOSE
        mock_debug_manager.start_performance_tracking.return_value = "test_op_id"
        mock_debug_manager.finish_performance_tracking.return_value = 0.1

        # Setup mock camera to simulate DXGI error
        mock_camera.grab.side_effect = [
            None,  # First attempt fails
            None,  # Second attempt fails
            Exception("DXGI_ERROR_INVALID_CALL")  # Third attempt throws error
        ]

        # Mock the BetterCam DXGI error
        dxgi_error = Exception()
        dxgi_error.args = (-2005270527, 'The application made a call that is invalid.')
        mock_camera.grab.side_effect = dxgi_error

        # Test the capture
        region = (0, 0, 100, 100)

        with patch('btd6_auto.vision.logging') as mock_logging:
            result = capture_region(region)
            assert result is None

            # Verify error was logged
            mock_logging.exception.assert_called_with("BetterCam grab error in capture_region")

    def test_performance_overhead_in_debug_mode(self):
        """Test that debug mode performance tracking adds minimal overhead."""
        config = {
            "enabled": True,
            "level": 3,
            "log_to_file": False,
            "log_to_console": False,
            "performance_tracking": True
        }
        debug_manager = DebugManager(config)

        # Measure time for multiple performance tracking operations
        start_time = time.time()

        for i in range(100):
            op_id = debug_manager.start_performance_tracking(f"test_op_{i}")
            debug_manager.add_checkpoint(op_id, "checkpoint1")
            debug_manager.add_checkpoint(op_id, "checkpoint2")
            debug_manager.finish_performance_tracking(op_id)

        end_time = time.time()
        total_time = end_time - start_time

        # Performance tracking should not add significant overhead
        # Allow up to 0.1 seconds for 100 operations (1ms per operation)
        assert total_time < 0.1, f"Performance tracking too slow: {total_time:.3f}s for 100 ops"

    @patch('btd6_auto.vision.cv2.cvtColor')
    @patch('btd6_auto.vision._CAMERA')
    def test_capture_region_timing_with_verbose_logging(self, mock_camera, mock_cvtcolor):
        """Test that verbose logging doesn't interfere with capture timing."""
        # Setup mock debug manager for verbose mode
        mock_debug_manager = Mock()
        mock_debug_manager.enabled = True
        mock_debug_manager.level.value = 3
        mock_debug_manager.start_performance_tracking.return_value = "test_id"
        mock_debug_manager.finish_performance_tracking.return_value = 0.05

        # Mock successful capture
        mock_img = Mock()
        mock_img.shape = (100, 100, 4)
        mock_camera.grab.return_value = mock_img
        mock_cvtcolor.return_value = Mock()

        # Patch the debug manager in vision module
        with patch('btd6_auto.vision._DEBUG_MANAGER', mock_debug_manager):
            with patch('btd6_auto.vision.time.sleep'):  # Skip sleep for timing test
                start_time = time.time()
                result = capture_region((0, 0, 100, 100))
                end_time = time.time()

        # In verbose mode (level 3), performance tracking should be disabled
        # So start_performance_tracking should not have been called
        assert not mock_debug_manager.start_performance_tracking.called
        assert not mock_debug_manager.add_checkpoint.called

        # Verify result is not None
        assert result is not None

    def test_debug_mode_config_impact_on_vision(self):
        """Test how different debug configurations affect vision operations."""
        configs = [
            {"enabled": False, "level": 0},  # No debug
            {"enabled": True, "level": 1, "performance_tracking": False},  # Basic
            {"enabled": True, "level": 2, "performance_tracking": True},   # Detailed
            {"enabled": True, "level": 3, "performance_tracking": True},   # Verbose
        ]

        for config in configs:
            debug_manager = DebugManager(config)

            # Test operation tracking
            op_id = debug_manager.start_performance_tracking("test")

            # In verbose mode (level 3), tracking should return None to prevent overhead
            # Also should return None if performance_tracking is disabled or debug is disabled
            expected_none = (
                not config.get("enabled", False) or
                not config.get("performance_tracking", True) or
                config.get("level", 0) >= 3
            )

            if expected_none:
                assert op_id is None
            else:
                assert op_id is not None

            if op_id:
                duration = debug_manager.finish_performance_tracking(op_id)
                if config["enabled"]:
                    assert duration is not None
                else:
                    assert duration is None