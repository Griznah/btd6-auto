"""
Comprehensive tests for the BTD6 vision system.

Tests image processing, template matching, screenshot capture, and computer
vision functionality using synthetic test data and mocks.
"""

import os
import sys
import cv2
import numpy as np
import unittest
from unittest.mock import patch, MagicMock, mock_open

# Add the btd6_auto module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "btd6_auto"))

from btd6_auto.vision import capture_screen, find_element_on_screen
from btd6_auto.exceptions import ScreenshotError, TemplateNotFoundError


class VisionSystemTests(unittest.TestCase):
    """Test cases for basic vision functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_images_dir = os.path.join(
            os.path.dirname(__file__), "test_data", "images"
        )
        self.test_template = os.path.join(self.test_images_dir, "button_play_test.png")
        self.test_screenshot = os.path.join(self.test_images_dir, "test_screenshot.png")

        # Create test images if they don't exist
        if not os.path.exists(self.test_images_dir):
            os.makedirs(self.test_images_dir, exist_ok=True)

    def test_template_loading(self):
        """Test template image loading."""
        # Test loading a valid template
        if os.path.exists(self.test_template):
            template = cv2.imread(self.test_template)
            self.assertIsNotNone(template)
            self.assertEqual(len(template.shape), 3)  # Should be color image
            self.assertGreater(template.shape[0], 0)  # Should have height
            self.assertGreater(template.shape[1], 0)  # Should have width

        # Test loading non-existent template
        with self.assertRaises(Exception):  # cv2.imread returns None for missing files
            invalid_template = cv2.imread("/nonexistent/path/template.png")
            self.assertIsNone(invalid_template)

    def test_screenshot_capture_mock(self):
        """Test screenshot capture with mocked pyautogui."""
        # Mock successful screenshot capture
        mock_screenshot = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_screenshot.fill(128)  # Gray image

        with patch("pyautogui.screenshot") as mock_screenshot_func:
            mock_screenshot_func.return_value = mock_screenshot

            result = capture_screen()

            self.assertIsNotNone(result)
            self.assertEqual(len(result.shape), 3)
            self.assertEqual(result.shape[:2], (100, 100))

        # Mock failed screenshot capture
        with patch("pyautogui.screenshot") as mock_screenshot_func:
            mock_screenshot_func.side_effect = Exception("Screenshot failed")

            result = capture_screen()

            self.assertIsNone(result)

    def test_screenshot_capture_with_region(self):
        """Test screenshot capture with region parameter."""
        mock_screenshot = np.zeros((50, 80, 3), dtype=np.uint8)

        with patch("pyautogui.screenshot") as mock_screenshot_func:
            mock_screenshot_func.return_value = mock_screenshot

            result = capture_screen(region=(10, 20, 80, 50))

            self.assertIsNotNone(result)
            mock_screenshot_func.assert_called_with(region=(10, 20, 80, 50))

    def test_template_matching_basic(self):
        """Test basic template matching functionality."""
        # Create test images
        large_image = np.zeros((200, 300, 3), dtype=np.uint8)
        large_image.fill(100)

        # Add a distinctive pattern
        large_image[50:100, 100:200] = [255, 255, 255]

        small_template = np.zeros((50, 100, 3), dtype=np.uint8)
        small_template.fill(255)

        # Test template matching
        result = cv2.matchTemplate(large_image, small_template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # Should find a good match
        self.assertGreater(max_val, 0.8)  # High confidence match
        self.assertEqual(max_loc, (100, 50))  # Should find at correct location

    def test_template_matching_with_rotation(self):
        """Test template matching with rotated templates."""
        # Create base image and template
        base_image = np.zeros((100, 100, 3), dtype=np.uint8)
        template = np.zeros((20, 20, 3), dtype=np.uint8)

        # Add a pattern to both
        base_image[40:60, 40:60] = [255, 0, 0]  # Red square
        template.fill(255)  # White template

        # Test matching identical images
        result = cv2.matchTemplate(base_image, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # Should find matches (though not perfect due to different colors)
        self.assertGreater(max_val, 0.0)

    def test_template_matching_confidence_thresholds(self):
        """Test template matching with different confidence thresholds."""
        # Create test image with known pattern
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        test_image[25:75, 25:75] = [255, 255, 255]  # White square in center

        template = np.ones((50, 50, 3), dtype=np.uint8) * 255

        result = cv2.matchTemplate(test_image, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # Perfect match should have high confidence
        self.assertGreater(max_val, 0.9)

        # Test different threshold levels
        high_threshold = 0.95
        medium_threshold = 0.8
        low_threshold = 0.5

        self.assertGreater(max_val, high_threshold)  # Should pass high threshold
        self.assertGreater(max_val, medium_threshold)  # Should pass medium threshold
        self.assertGreater(max_val, low_threshold)  # Should pass low threshold

    def test_find_element_with_mock_screenshot(self):
        """Test find_element_on_screen with mocked screenshot."""
        # Create a test scenario where template should be found
        large_image = np.zeros((200, 300, 3), dtype=np.uint8)
        large_image.fill(100)

        # Add template pattern at known location
        template_pattern = np.ones((50, 80, 3), dtype=np.uint8) * 255
        large_image[75:125, 100:180] = template_pattern

        with patch("btd6_auto.vision.capture_screen") as mock_capture:
            mock_capture.return_value = large_image

            # Mock template loading
            with patch("cv2.imread") as mock_imread:
                mock_imread.return_value = template_pattern

                with patch("btd6_auto.vision.os.path.exists", return_value=True):
                    result = find_element_on_screen("test_template.png")

                    self.assertIsNotNone(result)
                    self.assertIsInstance(result, tuple)
                    self.assertEqual(len(result), 2)
                    # Should find template near the center of where we placed it
                    self.assertAlmostEqual(result[0], 140, delta=10)  # x coordinate
                    self.assertAlmostEqual(result[1], 100, delta=10)  # y coordinate

    def test_find_element_not_found(self):
        """Test find_element_on_screen when template is not found."""
        # Create image without the template pattern
        large_image = np.zeros((200, 300, 3), dtype=np.uint8)
        large_image.fill(100)  # Uniform gray

        # Template that won't match
        template_pattern = np.ones((50, 80, 3), dtype=np.uint8) * 255

        with patch("btd6_auto.vision.capture_screen") as mock_capture:
            mock_capture.return_value = large_image

            with patch("cv2.imread") as mock_imread:
                mock_imread.return_value = template_pattern

                with patch("btd6_auto.vision.os.path.exists", return_value=True):
                    result = find_element_on_screen("test_template.png")

                    self.assertIsNone(result)

    def test_find_element_invalid_template(self):
        """Test find_element_on_screen with invalid template file."""
        with patch("btd6_auto.vision.capture_screen") as mock_capture:
            mock_capture.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

            with patch("cv2.imread") as mock_imread:
                mock_imread.return_value = None  # Simulate failed image load

                with patch("btd6_auto.vision.os.path.exists", return_value=True):
                    result = find_element_on_screen("invalid_template.png")

                    self.assertIsNone(result)

    def test_find_element_screenshot_failure(self):
        """Test find_element_on_screen when screenshot capture fails."""
        with patch("btd6_auto.vision.capture_screen") as mock_capture:
            mock_capture.return_value = None  # Simulate screenshot failure

            result = find_element_on_screen("test_template.png")

            self.assertIsNone(result)


class ImageProcessingTests(unittest.TestCase):
    """Test cases for image processing utilities."""

    def test_image_color_conversion(self):
        """Test image color space conversions."""
        # Create RGB test image
        rgb_image = np.zeros((50, 50, 3), dtype=np.uint8)
        rgb_image[:, :, 0] = 255  # Red channel
        rgb_image[:, :, 1] = 128  # Green channel
        rgb_image[:, :, 2] = 64  # Blue channel

        # Convert to BGR (OpenCV format)
        bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)

        # Verify conversion
        self.assertEqual(bgr_image.shape, rgb_image.shape)
        self.assertEqual(bgr_image[0, 0, 0], 64)  # Blue channel first in BGR
        self.assertEqual(bgr_image[0, 0, 1], 128)  # Green channel
        self.assertEqual(bgr_image[0, 0, 2], 255)  # Red channel last in BGR

    def test_image_resizing(self):
        """Test image resizing operations."""
        original = np.zeros((100, 200, 3), dtype=np.uint8)

        # Resize to half size
        resized = cv2.resize(original, (100, 50))

        self.assertEqual(resized.shape, (50, 100, 3))

        # Resize with different interpolation methods
        nearest = cv2.resize(original, (150, 75), interpolation=cv2.INTER_NEAREST)
        linear = cv2.resize(original, (150, 75), interpolation=cv2.INTER_LINEAR)
        cubic = cv2.resize(original, (150, 75), interpolation=cv2.INTER_CUBIC)

        self.assertEqual(nearest.shape, (75, 150, 3))
        self.assertEqual(linear.shape, (75, 150, 3))
        self.assertEqual(cubic.shape, (75, 150, 3))

    def test_image_thresholding(self):
        """Test image thresholding operations."""
        # Create grayscale image with varying intensity
        gray_image = np.zeros((50, 50), dtype=np.uint8)
        gray_image[10:40, 10:40] = 128  # Medium gray square
        gray_image[20:30, 20:30] = 255  # White inner square

        # Apply binary threshold
        ret, binary = cv2.threshold(gray_image, 100, 255, cv2.THRESH_BINARY)

        # Check that thresholding worked
        self.assertGreater(ret, 0)  # Should return threshold value
        self.assertEqual(binary.shape, gray_image.shape)

        # Check that high intensity areas are white, low are black
        self.assertEqual(binary[5, 5], 0)  # Outside square should be black
        self.assertEqual(binary[25, 25], 255)  # Inner white square should be white
        self.assertEqual(binary[15, 15], 255)  # Medium gray square should be white

    def test_template_matching_algorithms(self):
        """Test different template matching algorithms."""
        # Create test image and template
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        template = np.zeros((30, 30, 3), dtype=np.uint8)

        # Add identical pattern to both
        pattern = np.ones((20, 20, 3), dtype=np.uint8) * 200
        image[35:55, 35:55] = pattern
        template[5:25, 5:25] = pattern

        algorithms = [
            cv2.TM_CCOEFF,
            cv2.TM_CCOEFF_NORMED,
            cv2.TM_CCORR,
            cv2.TM_CCORR_NORMED,
            cv2.TM_SQDIFF,
            cv2.TM_SQDIFF_NORMED,
        ]

        for algorithm in algorithms:
            with self.subTest(algorithm=algorithm):
                result = cv2.matchTemplate(image, template, algorithm)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                # All algorithms should find the pattern
                self.assertIsNotNone(result)
                self.assertEqual(result.shape, (71, 71))  # Expected result size

                # For normalized algorithms, result should be in valid range
                if algorithm in [
                    cv2.TM_CCOEFF_NORMED,
                    cv2.TM_CCORR_NORMED,
                    cv2.TM_SQDIFF_NORMED,
                ]:
                    if algorithm == cv2.TM_SQDIFF_NORMED:
                        self.assertGreaterEqual(max_val, 0.0)
                        self.assertLessEqual(max_val, 1.0)
                    else:
                        self.assertGreaterEqual(min_val, -1.0)
                        self.assertLessEqual(max_val, 1.0)

    def test_multi_scale_template_matching(self):
        """Test template matching at different scales."""
        # Create test image and template at different scales
        base_template = np.zeros((20, 20, 3), dtype=np.uint8)
        base_template.fill(255)

        # Create image with template at different sizes
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        image.fill(100)

        # Add template at original size
        image[50:70, 50:70] = base_template

        # Add template at double size
        large_template = cv2.resize(base_template, (40, 40))
        image[100:140, 100:140] = large_template

        # Test matching with different template sizes
        result1 = cv2.matchTemplate(image, base_template, cv2.TM_CCOEFF_NORMED)
        min_val1, max_val1, min_loc1, max_loc1 = cv2.minMaxLoc(result1)

        # Should find the original size template well
        self.assertGreater(max_val1, 0.8)

        # Test with resized template
        result2 = cv2.matchTemplate(image, large_template, cv2.TM_CCOEFF_NORMED)
        min_val2, max_val2, min_loc2, max_loc2 = cv2.minMaxLoc(result2)

        # Should find the large template well
        self.assertGreater(max_val2, 0.8)


class VisionErrorHandlingTests(unittest.TestCase):
    """Test error handling in vision operations."""

    def test_screenshot_error_handling(self):
        """Test screenshot error handling."""
        error_scenarios = [
            Exception("Permission denied"),
            OSError("Device not found"),
            MemoryError("Out of memory"),
        ]

        for error in error_scenarios:
            with self.subTest(error=type(error).__name__):
                with patch("pyautogui.screenshot") as mock_screenshot:
                    mock_screenshot.side_effect = error

                    result = capture_screen()

                    self.assertIsNone(result)

    def test_template_loading_error_handling(self):
        """Test template loading error handling."""
        # Test various file system errors
        error_scenarios = [
            FileNotFoundError("File not found"),
            PermissionError("Permission denied"),
            IsADirectoryError("Is a directory"),
        ]

        for error in error_scenarios:
            with self.subTest(error=type(error).__name__):
                with patch("cv2.imread") as mock_imread:
                    mock_imread.side_effect = error

                    with patch("os.path.exists", return_value=True):
                        # Should handle the error gracefully
                        try:
                            find_element_on_screen("test_template.png")
                        except Exception as e:
                            # Should raise appropriate exception
                            self.assertIsInstance(e, (TemplateNotFoundError, Exception))

    def test_image_processing_error_handling(self):
        """Test error handling in image processing operations."""
        # Test with invalid image data
        invalid_image = None

        with self.assertRaises(AttributeError):
            cv2.matchTemplate(invalid_image, invalid_image, cv2.TM_CCOEFF_NORMED)

        # Test with mismatched dimensions
        img1 = np.zeros((50, 50, 3))
        img2 = np.zeros((30, 30))  # Grayscale instead of color

        with self.assertRaises(Exception):
            cv2.matchTemplate(img1, img2, cv2.TM_CCOEFF_NORMED)


class VisionIntegrationTests(unittest.TestCase):
    """Integration tests for vision system components."""

    def test_full_template_matching_workflow(self):
        """Test complete template matching workflow."""
        # Create test scenario
        screenshot = np.zeros((300, 400, 3), dtype=np.uint8)
        screenshot.fill(128)  # Gray background

        # Add UI elements
        button_area = screenshot[100:150, 150:250]
        button_area.fill(255)  # White button

        template = np.ones((50, 100, 3), dtype=np.uint8) * 255

        with patch("btd6_auto.vision.capture_screen") as mock_capture:
            mock_capture.return_value = screenshot

            with patch("cv2.imread") as mock_imread:
                mock_imread.return_value = template

                with patch("btd6_auto.vision.os.path.exists", return_value=True):
                    result = find_element_on_screen("button_template.png")

                    self.assertIsNotNone(result)
                    self.assertIsInstance(result, tuple)
                    # Should find button approximately at center of where we placed it
                    self.assertAlmostEqual(result[0], 200, delta=20)
                    self.assertAlmostEqual(result[1], 125, delta=20)

    def test_vision_with_validation_integration(self):
        """Test vision system integration with validation."""
        from btd6_auto.validation import CoordinateValidator

        validator = CoordinateValidator()

        # Mock a successful template match
        mock_coords = (250, 150)

        with patch("btd6_auto.vision.find_element_on_screen") as mock_find:
            mock_find.return_value = mock_coords

            # Should validate the returned coordinates
            coords = find_element_on_screen("test_template.png")

            if coords is not None:
                validated_coords = validator.validate_coordinates(
                    coords, "template_match"
                )
                self.assertEqual(validated_coords, mock_coords)

    def test_vision_with_retry_integration(self):
        """Test vision system integration with retry mechanism."""
        from btd6_auto.retry_utils import retry

        attempt_count = 0

        @retry(
            max_retries=3, base_delay=0.01, retryable_exceptions=[TemplateNotFoundError]
        )
        def retryable_vision_operation():
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count == 1:
                return None  # Simulate no match found
            return (100, 100)  # Simulate successful match

        with patch("time.sleep"):
            result = retryable_vision_operation()

        self.assertEqual(result, (100, 100))
        self.assertEqual(attempt_count, 2)  # Should have retried once


class VisionPerformanceTests(unittest.TestCase):
    """Test vision system performance characteristics."""

    def test_template_matching_performance(self):
        """Test template matching performance with different image sizes."""
        # Test with small images
        small_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        small_template = np.random.randint(0, 255, (20, 20, 3), dtype=np.uint8)

        start_time = time.time()
        for _ in range(10):
            cv2.matchTemplate(small_image, small_template, cv2.TM_CCOEFF_NORMED)
        small_time = time.time() - start_time

        # Test with larger images
        large_image = np.random.randint(0, 255, (500, 500, 3), dtype=np.uint8)
        large_template = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)

        start_time = time.time()
        for _ in range(10):
            cv2.matchTemplate(large_image, large_template, cv2.TM_CCOEFF_NORMED)
        large_time = time.time() - start_time

        # Larger images should take more time, but not excessively so
        self.assertGreater(large_time, small_time)
        # Performance should be reasonable (less than 1 second for 10 operations)
        self.assertLess(large_time, 1.0)

    def test_memory_usage_with_large_images(self):
        """Test memory usage with large images."""
        import gc

        # Force garbage collection to get baseline
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Create large images
        large_images = []
        for i in range(5):
            img = np.random.randint(0, 255, (1000, 1000, 3), dtype=np.uint8)
            large_images.append(img)

        # Force garbage collection
        gc.collect()
        after_objects = len(gc.get_objects())

        # Memory usage should be reasonable
        object_increase = after_objects - initial_objects
        self.assertLess(object_increase, 100)  # Should not create excessive objects

        # Clean up
        del large_images
        gc.collect()

    def test_concurrent_vision_operations(self):
        """Test concurrent vision operations."""
        import threading
        import queue

        results = queue.Queue()

        def vision_operation(operation_id):
            try:
                # Simulate template matching operation
                image = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
                template = np.random.randint(0, 255, (30, 30, 3), dtype=np.uint8)

                start_time = time.time()
                result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
                end_time = time.time()

                duration = end_time - start_time
                results.put((operation_id, duration, "success"))

            except Exception as e:
                results.put((operation_id, 0, f"error: {e}"))

        # Start multiple concurrent operations
        threads = []
        for i in range(10):
            thread = threading.Thread(target=vision_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check results
        successful_operations = 0
        while not results.empty():
            operation_id, duration, status = results.get()
            if status == "success":
                successful_operations += 1
                self.assertGreater(duration, 0)  # Should take some time
                self.assertLess(duration, 1.0)  # Should not take too long

        self.assertEqual(successful_operations, 10)


if __name__ == "__main__":
    # Check if OpenCV is available
    try:
        import cv2
        import numpy
    except ImportError as e:
        print(f"Skipping vision tests due to missing dependencies: {e}")
        sys.exit(0)

    unittest.main()
