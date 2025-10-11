"""
Comprehensive tests for the BTD6 validation system.

Tests coordinate validation, input validation, bounds checking, and error handling
without requiring the actual game or GUI interactions.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add the btd6_auto module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'btd6_auto'))

from btd6_auto.validation import CoordinateValidator, InputValidator
from btd6_auto.exceptions import (
    InvalidCoordinateError,
    InvalidKeyError,
    BTD6AutomationError,
    WindowNotFoundError,
    WindowActivationError
)
from tests.test_data.coordinates import (
    VALID_COORDINATES,
    INVALID_COORDINATES,
    CONFLICTING_COORDINATES,
    SCREEN_RESOLUTIONS,
    EDGE_CASE_COORDINATES
)


class CoordinateValidatorTests(unittest.TestCase):
    """Test cases for coordinate validation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = CoordinateValidator()

    def test_screen_bounds_detection(self):
        """Test screen bounds detection functionality."""
        bounds = self.validator._get_screen_bounds()

        # Should return a dictionary with screen information
        self.assertIsInstance(bounds, dict)
        self.assertIn('primary', bounds)

        # Primary screen should have width and height
        primary_bounds = bounds['primary']
        self.assertIsInstance(primary_bounds, tuple)
        self.assertEqual(len(primary_bounds), 2)
        self.assertGreater(primary_bounds[0], 0)  # Width > 0
        self.assertGreater(primary_bounds[1], 0)  # Height > 0

    @patch('screeninfo.get_monitors')
    def test_screen_bounds_with_screeninfo(self, mock_get_monitors):
        """Test screen bounds detection using screeninfo library."""
        # Mock monitor objects
        mock_monitor1 = MagicMock()
        mock_monitor1.width = 1920
        mock_monitor1.height = 1080

        mock_monitor2 = MagicMock()
        mock_monitor2.width = 2560
        mock_monitor2.height = 1440

        mock_get_monitors.return_value = [mock_monitor1, mock_monitor2]

        validator = CoordinateValidator()
        bounds = validator._get_screen_bounds()

        # Should detect both monitors
        self.assertIn('monitor_0', bounds)
        self.assertIn('monitor_1', bounds)
        self.assertIn('primary', bounds)

        self.assertEqual(bounds['primary'], (1920, 1080))
        self.assertEqual(bounds['monitor_0'], (1920, 1080))
        self.assertEqual(bounds['monitor_1'], (2560, 1440))

    @patch('validation.tk')
    def test_screen_bounds_fallback_to_tkinter(self, mock_tk):
        """Test screen bounds detection falling back to tkinter."""
        # Mock screeninfo to fail, tkinter to succeed
        with patch('screeninfo.get_monitors', side_effect=Exception("screeninfo failed")):
            mock_root = MagicMock()
            mock_root.winfo_screenwidth.return_value = 1366
            mock_root.winfo_screenheight.return_value = 768
            mock_tk.Tk.return_value = mock_root

            validator = CoordinateValidator()
            bounds = validator._get_screen_bounds()

            self.assertEqual(bounds['primary'], (1366, 768))

    def test_coordinate_validation_success(self):
        """Test successful coordinate validation."""
        for coords in VALID_COORDINATES:
            with self.subTest(coords=coords):
                validated = self.validator.validate_coordinates(coords, "test")
                self.assertEqual(validated, coords)
                self.assertIsInstance(validated, tuple)

    def test_coordinate_validation_failures(self):
        """Test coordinate validation failures."""
        for coords in INVALID_COORDINATES:
            with self.subTest(coords=coords):
                with self.assertRaises(InvalidCoordinateError):
                    self.validator.validate_coordinates(coords, "test")

    def test_coordinate_bounds_checking(self):
        """Test coordinate bounds checking against screen size."""
        # Mock small screen size for testing
        with patch.object(self.validator, '_screen_bounds', {'primary': (100, 100)}):
            # Coordinates within bounds should pass
            valid_coords = (50, 50)
            validated = self.validator.validate_coordinates(valid_coords, "test")
            self.assertEqual(validated, valid_coords)

            # Coordinates outside bounds should fail
            invalid_coords = (150, 150)
            with self.assertRaises(InvalidCoordinateError):
                self.validator.validate_coordinates(invalid_coords, "test")

    def test_coordinate_conflict_detection(self):
        """Test detection of conflicting coordinates."""
        # Test with conflicting coordinates
        conflicts = self.validator.check_coordinate_conflicts(
            CONFLICTING_COORDINATES, min_distance=10
        )

        # Should detect conflicts between close coordinates
        self.assertGreater(len(conflicts), 0)

        # Test with non-conflicting coordinates
        no_conflicts = self.validator.check_coordinate_conflicts(
            [(10, 10), (100, 100), (200, 200)], min_distance=10
        )

        self.assertEqual(len(no_conflicts), 0)

    def test_coordinate_conflict_with_different_thresholds(self):
        """Test coordinate conflict detection with different distance thresholds."""
        test_coords = [(100, 100), (105, 105), (200, 200)]

        # With small threshold, should detect conflict
        conflicts_small = self.validator.check_coordinate_conflicts(
            test_coords, min_distance=10
        )
        self.assertGreater(len(conflicts_small), 0)

        # With large threshold, should not detect conflict
        conflicts_large = self.validator.check_coordinate_conflicts(
            test_coords, min_distance=200
        )
        self.assertEqual(len(conflicts_large), 0)

    def test_edge_case_coordinates(self):
        """Test validation of edge case coordinates."""
        for coords in EDGE_CASE_COORDINATES:
            with self.subTest(coords=coords):
                # These should all be valid (within reasonable screen bounds)
                validated = self.validator.validate_coordinates(coords, "edge_test")
                self.assertEqual(validated, coords)


class InputValidatorTests(unittest.TestCase):
    """Test cases for input validation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = InputValidator()

    def test_key_validation(self):
        """Test keyboard key validation."""
        # Valid keys
        valid_keys = ['q', 'w', 'e', 'r', 'a', 's', 'd', 'f']
        for key in valid_keys:
            with self.subTest(key=key):
                validated = self.validator.validate_key(key, "test")
                self.assertEqual(validated, key)

        # Invalid keys
        invalid_keys = ['qq', '', 'Q', 123, None]
        for key in invalid_keys:
            with self.subTest(key=key):
                with self.assertRaises(InvalidKeyError):
                    self.validator.validate_key(key, "test")

    def test_map_name_validation(self):
        """Test game map name validation."""
        # Valid map names (from the actual game)
        valid_maps = [
            "Monkey Meadow", "Scrapyard", "Riverside", "Clover", "Sunken Columns",
            "Balance", "Encrypted", "Bazaar", "Adora's Temple", "Spring Spring"
        ]

        for map_name in valid_maps:
            with self.subTest(map_name=map_name):
                validated = self.validator.validate_map_name(map_name, "test")
                self.assertEqual(validated, map_name)

        # Invalid map names
        invalid_maps = ["", "Nonexistent Map", None, 123]
        for map_name in invalid_maps:
            with self.subTest(map_name=map_name):
                with self.assertRaises(BTD6AutomationError):
                    self.validator.validate_map_name(map_name, "test")

    def test_difficulty_validation(self):
        """Test game difficulty validation."""
        valid_difficulties = ["Easy", "Medium", "Hard", "Impoppable"]

        for difficulty in valid_difficulties:
            with self.subTest(difficulty=difficulty):
                validated = self.validator.validate_difficulty(difficulty, "test")
                self.assertEqual(validated, difficulty)

        # Invalid difficulties
        invalid_difficulties = ["", "Impossible", "Beginner", None, 123]
        for difficulty in invalid_difficulties:
            with self.subTest(difficulty=difficulty):
                with self.assertRaises(BTD6AutomationError):
                    self.validator.validate_difficulty(difficulty, "test")

    def test_mode_validation(self):
        """Test game mode validation."""
        valid_modes = [
            "Standard", "Primary Only", "Deflation", "Reverse", "Half Cash",
            "Alternate Bloons Rounds", "Double HP MOABs", "CHIMPS", "Magic Only"
        ]

        for mode in valid_modes:
            with self.subTest(mode=mode):
                validated = self.validator.validate_mode(mode, "test")
                self.assertEqual(validated, mode)

        # Invalid modes
        invalid_modes = ["", "Invalid Mode", "Easy Mode", None, 123]
        for mode in invalid_modes:
            with self.subTest(mode=mode):
                with self.assertRaises(BTD6AutomationError):
                    self.validator.validate_mode(mode, "test")

    def test_timeout_validation(self):
        """Test timeout value validation."""
        # Valid timeouts
        valid_timeouts = [0.1, 1.0, 5.0, 10.0, 30.0]
        for timeout in valid_timeouts:
            with self.subTest(timeout=timeout):
                validated = self.validator.validate_timeout(timeout, "test")
                self.assertEqual(validated, timeout)

        # Invalid timeouts (negative)
        invalid_timeouts = [-1.0, -0.1, -10.0]
        for timeout in invalid_timeouts:
            with self.subTest(timeout=timeout):
                with self.assertRaises(BTD6AutomationError):
                    self.validator.validate_timeout(timeout, "test")

    def test_confidence_threshold_validation(self):
        """Test confidence threshold validation."""
        # Valid thresholds
        valid_thresholds = [0.1, 0.5, 0.8, 0.9, 1.0]
        for threshold in valid_thresholds:
            with self.subTest(threshold=threshold):
                validated = self.validator.validate_confidence_threshold(threshold, "test")
                self.assertEqual(validated, threshold)

        # Invalid thresholds (out of range)
        invalid_thresholds = [0.05, 1.1, -0.1, 2.0]
        for threshold in invalid_thresholds:
            with self.subTest(threshold=threshold):
                with self.assertRaises(BTD6AutomationError):
                    self.validator.validate_confidence_threshold(threshold, "test")

    def test_coordinate_range_validation(self):
        """Test coordinate range validation for specific UI elements."""
        # Test hero placement coordinates (should be in game area)
        hero_coords = (320, 250)
        validated = self.validator.validate_coordinate_range(hero_coords, "hero_placement")
        self.assertEqual(validated, hero_coords)

        # Test monkey placement coordinates
        monkey_coords = (440, 355)
        validated = self.validator.validate_coordinate_range(monkey_coords, "monkey_placement")
        self.assertEqual(validated, monkey_coords)

        # Test out-of-range coordinates
        invalid_coords = (50, 50)  # Too close to edge
        with self.assertRaises(BTD6AutomationError):
            self.validator.validate_coordinate_range(invalid_coords, "ui_element")

    def test_batch_coordinate_validation(self):
        """Test validation of multiple coordinates at once."""
        coordinate_batch = [
            (100, 100, "hero"),
            (200, 200, "monkey"),
            (300, 300, "upgrade_button")
        ]

        # All should validate successfully
        for coords, expected_coords, context in coordinate_batch:
            validated = self.validator.validate_coordinates_batch(
                [(coords[0], coords[1])], context
            )
            self.assertEqual(len(validated), 1)
            self.assertEqual(validated[0], (coords[0], coords[1]))

    def test_batch_validation_with_failures(self):
        """Test batch validation with some invalid coordinates."""
        mixed_batch = [
            (100, 100),      # Valid
            (-50, -50),      # Invalid
            (200, 200),      # Valid
            ("100", "200")   # Invalid
        ]

        # Should raise exception for invalid coordinates
        with self.assertRaises(BTD6AutomationError):
            self.validator.validate_coordinates_batch(mixed_batch, "batch_test")


class WindowValidationTests(unittest.TestCase):
    """Test cases for window validation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = InputValidator()

    @patch('pygetwindow.getWindowsWithTitle')
    def test_window_found_validation(self, mock_get_windows):
        """Test validation when game window is found."""
        # Mock a found window
        mock_window = MagicMock()
        mock_window.title = "BloonsTD6"
        mock_window.activate = MagicMock()
        mock_get_windows.return_value = [mock_window]

        # Should not raise exception
        try:
            self.validator.validate_window_found("BloonsTD6", "test")
        except WindowNotFoundError:
            self.fail("validate_window_found raised WindowNotFoundError unexpectedly")

    @patch('pygetwindow.getWindowsWithTitle')
    def test_window_not_found_validation(self, mock_get_windows):
        """Test validation when game window is not found."""
        # Mock no windows found
        mock_get_windows.return_value = []

        # Should raise WindowNotFoundError
        with self.assertRaises(WindowNotFoundError):
            self.validator.validate_window_found("BloonsTD6", "test")

    @patch('pygetwindow.getWindowsWithTitle')
    def test_window_activation_validation(self, mock_get_windows):
        """Test validation of window activation."""
        # Mock a window that fails to activate
        mock_window = MagicMock()
        mock_window.title = "BloonsTD6"
        mock_window.activate.side_effect = Exception("Activation failed")
        mock_get_windows.return_value = [mock_window]

        # Should raise WindowActivationError
        with self.assertRaises(WindowActivationError):
            self.validator.validate_window_activation("BloonsTD6", "test")


class ValidationIntegrationTests(unittest.TestCase):
    """Integration tests for the validation system."""

    def setUp(self):
        """Set up test fixtures."""
        self.coord_validator = CoordinateValidator()
        self.input_validator = InputValidator()

    def test_full_validation_workflow(self):
        """Test a complete validation workflow."""
        # Simulate validating a complete game setup
        test_data = {
            'hero_coords': (320, 250),
            'monkey_coords': (440, 355),
            'hero_key': 'u',
            'monkey_key': 'q',
            'selected_map': 'Monkey Meadow',
            'selected_difficulty': 'Easy',
            'selected_mode': 'Standard',
            'confidence_threshold': 0.85
        }

        # Validate all components
        validated_coords = [
            self.coord_validator.validate_coordinates(
                test_data['hero_coords'], 'hero_placement'
            ),
            self.coord_validator.validate_coordinates(
                test_data['monkey_coords'], 'monkey_placement'
            )
        ]

        validated_keys = [
            self.input_validator.validate_key(test_data['hero_key'], 'hero_selection'),
            self.input_validator.validate_key(test_data['monkey_key'], 'monkey_selection')
        ]

        validated_map = self.input_validator.validate_map_name(
            test_data['selected_map'], 'map_selection'
        )
        validated_difficulty = self.input_validator.validate_difficulty(
            test_data['selected_difficulty'], 'difficulty_selection'
        )
        validated_mode = self.input_validator.validate_mode(
            test_data['selected_mode'], 'mode_selection'
        )
        validated_threshold = self.input_validator.validate_confidence_threshold(
            test_data['confidence_threshold'], 'template_matching'
        )

        # All validations should succeed and return expected values
        self.assertEqual(validated_coords[0], (320, 250))
        self.assertEqual(validated_coords[1], (440, 355))
        self.assertEqual(validated_keys[0], 'u')
        self.assertEqual(validated_keys[1], 'q')
        self.assertEqual(validated_map, 'Monkey Meadow')
        self.assertEqual(validated_difficulty, 'Easy')
        self.assertEqual(validated_mode, 'Standard')
        self.assertEqual(validated_threshold, 0.85)

    def test_validation_error_propagation(self):
        """Test that validation errors are properly propagated."""
        # Test with invalid data that should cause multiple validation failures
        invalid_data = {
            'hero_coords': (-100, -100),  # Invalid coordinates
            'hero_key': 'uu',             # Invalid key (too long)
            'selected_map': 'Invalid Map', # Invalid map
            'confidence_threshold': 1.5   # Invalid threshold (too high)
        }

        # Should raise appropriate exceptions for each invalid field
        with self.assertRaises(InvalidCoordinateError):
            self.coord_validator.validate_coordinates(
                invalid_data['hero_coords'], 'hero_placement'
            )

        with self.assertRaises(InvalidKeyError):
            self.input_validator.validate_key(
                invalid_data['hero_key'], 'hero_selection'
            )

        with self.assertRaises(BTD6AutomationError):
            self.input_validator.validate_map_name(
                invalid_data['selected_map'], 'map_selection'
            )

        with self.assertRaises(BTD6AutomationError):
            self.input_validator.validate_confidence_threshold(
                invalid_data['confidence_threshold'], 'template_matching'
            )


if __name__ == '__main__':
    unittest.main()
