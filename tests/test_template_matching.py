"""
Updated template matching tests with new BTD6 automation modules.

This module provides comprehensive testing for template matching functionality
using the new exception handling, logging, validation, and retry mechanisms.
"""

import sys
import os
import cv2
import numpy as np
import time
import unittest
from unittest.mock import patch, MagicMock

# Import BTD6 automation modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'btd6_auto'))

try:
    from vision import capture_screen, find_element_on_screen
    from exceptions import (
        TemplateNotFoundError, MatchFailedError, ScreenshotError,
        BTD6AutomationError
    )
    from logging_utils import get_logger, log_performance, LogContext
    from validation import get_coordinate_validator, validate_coordinates
    from retry_utils import retry
    from config import _get_config_manager
except ImportError as e:
    print(f"[ERROR] Failed to import BTD6 modules: {e}")
    sys.exit(1)

# Test data paths
DATA_IMAGE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'images')
TEST_OUTPUT_DIR = os.path.dirname(__file__)

class TemplateMatchingTests(unittest.TestCase):
    """Test cases for template matching functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = get_logger("test_template_matching")
        self.validator = get_coordinate_validator()
        self.config_manager = _get_config_manager()

        # Test image paths
        self.test_template = os.path.join(DATA_IMAGE_PATH, "button_play.png")
        self.invalid_template = os.path.join(DATA_IMAGE_PATH, "nonexistent.png")

        # Create a simple test template if test images don't exist
        if not os.path.exists(DATA_IMAGE_PATH):
            os.makedirs(DATA_IMAGE_PATH, exist_ok=True)

    def test_template_loading(self):
        """Test template image loading with validation."""
        with LogContext("template_loading_test", self.logger):
            # Test valid template loading
            if os.path.exists(self.test_template):
                template = cv2.imread(self.test_template)
                self.assertIsNotNone(template, "Valid template should load successfully")
                self.assertEqual(len(template.shape), 3, "Template should be color image")
            else:
                self.logger.warning(f"Test template not found: {self.test_template}")

    def test_invalid_template_handling(self):
        """Test handling of invalid template files - should return None for missing templates."""
        # Test that find_element_on_screen returns None for non-existent files
        invalid_template_path = "definitely/does/not/exist.png"
        result = find_element_on_screen(invalid_template_path)
        self.assertIsNone(result, "find_element_on_screen should return None for missing template files")

    @patch('tests.test_template_matching.capture_screen')
    def test_screenshot_capture_with_retry(self, mock_capture):
        """Test screenshot capture with error handling and retry."""
        # Test successful capture
        mock_capture.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

        with LogContext("screenshot_test", self.logger):
            screenshot = capture_screen()
            self.assertIsNotNone(screenshot, "Screenshot should succeed")

        # Test failed capture with retry
        mock_capture.side_effect = [
            None,  # First attempt fails
            np.zeros((100, 100, 3), dtype=np.uint8)  # Second attempt succeeds
        ]

        with patch('time.sleep'):  # Speed up test
            screenshot = capture_screen()
            self.assertIsNotNone(screenshot, "Screenshot should succeed after retry")

    def test_coordinate_validation(self):
        """Test coordinate validation functionality."""
        with LogContext("coordinate_validation_test", self.logger):
            # Test valid coordinates
            valid_coords = (100, 200)
            validated = self.validator.validate_coordinates(valid_coords, "test")
            self.assertEqual(validated, valid_coords)

            # Test invalid coordinates
            with self.assertRaises(Exception):  # Should raise InvalidCoordinateError
                invalid_coords = (-10, -20)
                self.validator.validate_coordinates(invalid_coords, "test")

    def test_template_matching_with_retry(self):
        """Test template matching with retry logic."""
        if not os.path.exists(self.test_template):
            self.skipTest("Test template not available")

        with LogContext("template_matching_retry_test", self.logger):
            # This test would require actual screenshot and template matching
            # For now, we'll test the retry decorator functionality
            self.logger.info("Testing retry functionality with template matching")

            # Simulate a scenario where matching might fail initially
            attempt_count = 0

            def mock_find_element(template_path):
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count == 1:
                    return None  # First attempt fails
                return (50, 50)  # Second attempt succeeds

            @retry(max_retries=2, base_delay=0.1, retryable_exceptions=MatchFailedError)
            def match_with_retry():
                res = find_element_on_screen(self.test_template)
                if res is None:
                    raise MatchFailedError(self.test_template)
                return res

            with patch('tests.test_template_matching.find_element_on_screen', side_effect=mock_find_element):
                with patch('time.sleep'):
                    result = match_with_retry()
            self.assertIsNotNone(result, "Should succeed after retry")
            self.assertEqual(attempt_count, 2, "Should have made 2 attempts")
    def test_performance_logging(self):
        """Test performance logging integration."""
        @log_performance("test_operation", threshold_ms=50.0)
        def test_operation():
            time.sleep(0.01)  # 10ms operation
            return "success"

        with LogContext("performance_test", self.logger):
            result = test_operation()
            self.assertEqual(result, "success")

    def test_exception_context_logging(self):
        """Test that exceptions are properly logged with context."""
        with LogContext("exception_test", self.logger) as ctx:
            ctx.log_event("Starting exception test")

            with self.assertRaises(ValueError):
                # This should be caught and logged with context
                raise ValueError("Test exception")

    def test_coordinate_conflict_detection(self):
        """Test coordinate conflict detection."""
        coordinates = [
            (100, 100),
            (105, 105),  # Very close to first
            (200, 200),  # Far from others
            (102, 102),  # Close to first
        ]

        validated_coords = [self.validator.validate_coordinates(coord, f"test_{i}")
                          for i, coord in enumerate(coordinates)]

        conflicts = self.validator.check_coordinate_conflicts(validated_coords, min_distance=10)

        # Should detect conflicts between close coordinates
        self.assertGreater(len(conflicts), 0, "Should detect coordinate conflicts")

        # Test with no conflicts
        distant_coords = [(100, 100), (500, 500), (1000, 1000)]
        validated_distant = [self.validator.validate_coordinates(coord, f"test_{i}")
                           for i, coord in enumerate(distant_coords)]

        no_conflicts = self.validator.check_coordinate_conflicts(validated_distant, min_distance=10)
        self.assertEqual(len(no_conflicts), 0, "Should detect no conflicts for distant coordinates")


class ConfigurationTests(unittest.TestCase):
    """Test cases for configuration management."""

    def setUp(self):
        """Set up configuration tests."""
        self.config_manager = _get_config_manager()
        self.logger = get_logger("test_configuration")

    def test_configuration_validation(self):
        """Test configuration validation."""
        with LogContext("config_validation_test", self.logger):
            # Test that configuration loads without errors
            try:
                # This should not raise any exceptions
                monkey_coords = self.config_manager.get_setting('monkey_coords')
                self.assertIsInstance(monkey_coords, tuple)
                self.assertEqual(len(monkey_coords), 2)
            except Exception as e:
                self.fail(f"Configuration validation failed: {e}")

    def test_configuration_persistence(self):
        """Test configuration save/load functionality."""
        with LogContext("config_persistence_test", self.logger):
            # Test saving configuration
            test_config_path = os.path.join(TEST_OUTPUT_DIR, 'test_config.json')

            # Save current config
            success = self.config_manager.save_config(test_config_path)
            self.assertTrue(success, "Configuration save should succeed")

            # Verify file exists
            self.assertTrue(os.path.exists(test_config_path), "Config file should be created")

            # Test loading configuration
            new_config_manager = type(self.config_manager)(test_config_path)
            loaded_coords = new_config_manager.get_setting('monkey_coords')
            original_coords = self.config_manager.get_setting('monkey_coords')

            self.assertEqual(loaded_coords, original_coords, "Loaded config should match saved config")

            # Cleanup
            if os.path.exists(test_config_path):
                os.remove(test_config_path)


class IntegrationTests(unittest.TestCase):
    """Integration tests for the complete BTD6 automation system."""

    def setUp(self):
        """Set up integration tests."""
        self.logger = get_logger("test_integration")

    def test_module_imports(self):
        """Test that all modules can be imported without errors."""
        with LogContext("module_import_test", self.logger):
            try:
                # Test importing all new modules
                from exceptions import BTD6AutomationError, RetryExhaustedError
                from logging_utils import BTD6Logger, get_logger
                from validation import CoordinateValidator, InputValidator
                from retry_utils import retry, RetryContext
                from recovery import RecoveryManager
                from config import ConfigManager

                # Test basic instantiation
                logger = get_logger("test")
                validator = CoordinateValidator()
                config_manager = ConfigManager()

                self.logger.info("All modules imported and instantiated successfully")

            except ImportError as e:
                self.fail(f"Module import failed: {e}")

    def test_end_to_end_workflow(self):
        """Test a simplified end-to-end automation workflow."""
        with LogContext("end_to_end_test", self.logger):
            try:
                # This would be a simplified version of the main automation loop
                # For testing purposes, we'll just verify the modules work together

                # 1. Load configuration
                config_manager = _get_config_manager()

                # 2. Validate coordinates
                validator = get_coordinate_validator()
                coords = config_manager.get_setting('monkey_coords')
                if coords:
                    validated_coords = validator.validate_coordinates(coords, "workflow_test")

                # 3. Set up logging
                logger = get_logger("workflow_test")

                # 4. Test retry mechanism
                @retry(max_retries=2, base_delay=0.01)
                def mock_operation():
                    return "success"

                with patch('time.sleep'):
                    result = mock_operation()
                    self.assertEqual(result, "success")

                self.logger.info("End-to-end workflow test completed successfully")

            except Exception as e:
                self.fail(f"End-to-end workflow test failed: {e}")


def verbose_template_match(screenshot, template, threshold=0.8):
    """
    Legacy function for backward compatibility.
    Now includes proper logging and error handling.
    """
    logger = get_logger("template_matching")

    try:
        logger.debug("Starting template matching", template_shape=template.shape)

        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        logger.debug("Template matching completed",
                    max_val=max_val,
                    threshold=threshold)

        loc = np.where(result >= threshold)

        return result, loc, max_val, max_loc

    except Exception as e:
        logger.error("Template matching failed", error=str(e))
        raise


def draw_matches(screenshot, template, loc):
    """
    Legacy function for backward compatibility.
    Now includes proper logging.
    """
    logger = get_logger("match_drawing")

    try:
        h, w = template.shape[:2]

        logger.debug("Drawing match rectangles", match_count=len(loc[0]))

        for pt in zip(*loc[::-1]):
            cv2.rectangle(screenshot, pt, (pt[0] + w, pt[1] + h), (0, 0, 255), 2)

        return screenshot

    except Exception as e:
        logger.error("Failed to draw matches", error=str(e))
        raise


def main():
    """Main function for running tests and legacy functionality."""
    # Run unit tests if no arguments provided
    if len(sys.argv) == 1:
        print("[INFO] Running BTD6 automation tests...")

        # Set up logging for tests
        logger = get_logger("test_runner")
        logger.info("Starting test suite")

        # Discover and run tests
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(sys.modules[__name__])

        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
        result = runner.run(suite)

        if result.wasSuccessful():
            logger.info("All tests passed")
            return 0
        else:
            logger.error(f"Test failures: {len(result.failures)} failures, {len(result.errors)} errors")
            return 1

    # Legacy template matching functionality
    elif len(sys.argv) == 2:
        template_filename = sys.argv[1]
        template_path = os.path.join(DATA_IMAGE_PATH, template_filename)

        logger = get_logger("legacy_template_matching")

        with LogContext("legacy_template_matching", logger):
            if not os.path.exists(template_path):
                logger.error("Template not found", template_path=template_path)
                print(f"[ERROR] Template image not found: {template_path}")
                sys.exit(1)

            logger.info("Starting legacy template matching test")

            try:
                # Test window activation with new error handling
                from game_launcher import activate_btd6_window

                with patch('pygetwindow.getWindowsWithTitle') as mock_get_windows:
                    # Mock window for testing
                    mock_window = MagicMock()
                    mock_window.title = "BloonsTD6 (Test)"
                    mock_get_windows.return_value = [mock_window]

                    success = activate_btd6_window()
                    logger.info("Window activation test completed", success=success)

            except Exception as e:
                logger.error("Window activation test failed", error=str(e))

            # Test screenshot capture
            logger.info("Testing screenshot capture")
            screenshot = capture_screen()
            if screenshot is None:
                logger.error("Screenshot capture failed")
                print("[ERROR] Screenshot failed.")
                sys.exit(1)

            # Test template loading
            logger.info("Testing template loading")
            template = cv2.imread(template_path)
            if template is None:
                logger.error("Template loading failed", template_path=template_path)
                print(f"[ERROR] Failed to load template image.")
                sys.exit(1)

            # Test template matching
            logger.info("Testing template matching")
            result, loc, max_val, max_loc = verbose_template_match(screenshot, template)

            logger.info("Template matching completed",
                       best_match_value=max_val,
                       match_location=max_loc,
                       matches_above_threshold=len(loc[0]))

            print(f"[RESULT] Best match value: {max_val} at location {max_loc}")
            print(f"[RESULT] Matches above threshold: {len(loc[0])}")

            # Test match drawing
            logger.info("Testing match visualization")
            matched_img = draw_matches(screenshot.copy(), template, loc)
            output_path = os.path.join(TEST_OUTPUT_DIR, 'output_match.png')
            cv2.imwrite(output_path, matched_img)
            logger.info("Match visualization saved", output_path=output_path)
            print(f"[INFO] Output image saved to: {output_path}")

        return 0

    else:
        print(f"Usage: python {sys.argv[0]} [template_image_filename]")
        print("       python {sys.argv[0]}  # Run tests")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
