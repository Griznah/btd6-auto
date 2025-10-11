"""
Comprehensive tests for the BTD6 configuration system.

Tests configuration loading, validation, persistence, and error handling
without requiring the actual game or GUI interactions.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'btd6_auto'))

from btd6_auto.config import ConfigManager, GameSettings
from btd6_auto.exceptions import BTD6AutomationError


class ConfigurationSystemTests(unittest.TestCase):
    """Test cases for configuration management."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_data', 'configs')
        self.valid_config_path = os.path.join(self.test_dir, 'valid_config.json')
        self.invalid_config_path = os.path.join(self.test_dir, 'invalid_config.json')
        self.malformed_config_path = os.path.join(self.test_dir, 'malformed_config.json')

        # Create a temporary directory for testing file operations
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up any temporary files
        for file in os.listdir(self.temp_dir):
            file_path = os.path.join(self.temp_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir(self.temp_dir)

    def test_game_settings_creation(self):
        """Test GameSettings dataclass creation and validation."""
        # Test valid settings creation
        settings = GameSettings()
        self.assertEqual(settings.monkey_type, "Dart Monkey")
        self.assertEqual(settings.monkey_coords, (440, 355))
        self.assertEqual(settings.hero_type, "Quincy")
        self.assertEqual(settings.selected_map, "Monkey Meadow")
        self.assertEqual(settings.selected_difficulty, "Easy")

    def test_coordinate_validation(self):
        """Test coordinate validation in GameSettings."""
        # Test valid coordinates
        settings = GameSettings()
        self.assertEqual(settings.monkey_coords, (440, 355))
        self.assertEqual(settings.hero_coords, (320, 250))

        # Test invalid coordinates (negative values)
        with self.assertRaises(ValueError) as cm:
            GameSettings(monkey_coords=(-100, -50))
        self.assertIn("must be non-negative", str(cm.exception))

        # Test invalid coordinate format (not a tuple)
        with self.assertRaises(ValueError) as cm:
            GameSettings(monkey_coords=[440, 355])  # List instead of tuple
        self.assertIn("must be a tuple", str(cm.exception))

        # Test invalid coordinate format (wrong length)
        with self.assertRaises(ValueError) as cm:
            GameSettings(monkey_coords=(440,))  # Single value
        self.assertIn("must be a tuple", str(cm.exception))

    def test_key_validation(self):
        """Test keyboard key validation in GameSettings."""
        # Test valid keys
        settings = GameSettings()
        self.assertEqual(settings.monkey_key, 'q')
        self.assertEqual(settings.hero_key, 'u')

        # Test invalid key (too long)
        with self.assertRaises(ValueError) as cm:
            GameSettings(monkey_key='qq')  # Two characters
        self.assertIn("must be a single character", str(cm.exception))

        # Test invalid key type (not string)
        with self.assertRaises(ValueError) as cm:
            GameSettings(monkey_key=123)  # Integer instead of string
        self.assertIn("must be a single character", str(cm.exception))

    def test_map_validation(self):
        """Test game map validation in GameSettings."""
        # Test valid map
        settings = GameSettings(selected_map="Scrapyard")
        self.assertEqual(settings.selected_map, "Scrapyard")

        # Test invalid map
        with self.assertRaises(ValueError) as cm:
            GameSettings(selected_map="Nonexistent Map")
        self.assertIn("not available", str(cm.exception))

    def test_difficulty_validation(self):
        """Test difficulty validation in GameSettings."""
        # Test valid difficulties
        for difficulty in ["Easy", "Medium", "Hard", "Impoppable"]:
            settings = GameSettings(selected_difficulty=difficulty)
            self.assertEqual(settings.selected_difficulty, difficulty)

        # Test invalid difficulty
        with self.assertRaises(ValueError) as cm:
            GameSettings(selected_difficulty="Impossible")
        self.assertIn("Difficulty must be one of", str(cm.exception))

    def test_mode_validation(self):
        """Test game mode validation in GameSettings."""
        # Test valid modes
        for mode in ["Standard", "Primary Only", "Deflation", "CHIMPS"]:
            settings = GameSettings(selected_mode=mode)
            self.assertEqual(settings.selected_mode, mode)

        # Test invalid mode
        with self.assertRaises(ValueError) as cm:
            GameSettings(selected_mode="Invalid Mode")
        self.assertIn("Mode must be one of", str(cm.exception))

    def test_timing_validation(self):
        """Test timing settings validation in GameSettings."""
        # Test valid click delay
        settings = GameSettings(click_delay=1.0)
        self.assertEqual(settings.click_delay, 1.0)

        # Test invalid click delay (negative)
        with self.assertRaises(ValueError) as cm:
            GameSettings(click_delay=-0.5)
        self.assertIn("must be between 0 and 5", str(cm.exception))

        # Test invalid click delay (too high)
        with self.assertRaises(ValueError) as cm:
            GameSettings(click_delay=10.0)
        self.assertIn("must be between 0 and 5", str(cm.exception))

    def test_confidence_threshold_validation(self):
        """Test confidence threshold validation in GameSettings."""
        # Test valid confidence threshold
        settings = GameSettings(confidence_threshold=0.8)
        self.assertEqual(settings.confidence_threshold, 0.8)

        # Test invalid confidence threshold (too low)
        with self.assertRaises(ValueError) as cm:
            GameSettings(confidence_threshold=0.05)
        self.assertIn("must be between 0.1 and 1.0", str(cm.exception))

        # Test invalid confidence threshold (too high)
        with self.assertRaises(ValueError) as cm:
            GameSettings(confidence_threshold=1.5)
        self.assertIn("must be between 0.1 and 1.0", str(cm.exception))

    def test_config_manager_initialization(self):
        """Test ConfigManager initialization."""
        # Test initialization without config file
        config_manager = ConfigManager()
        self.assertIsNotNone(config_manager.settings)
        self.assertIsInstance(config_manager.settings, GameSettings)

        # Test initialization with custom config path
        custom_config_path = os.path.join(self.temp_dir, 'custom_config.json')
        config_manager = ConfigManager(custom_config_path)
        self.assertEqual(config_manager.config_path, custom_config_path)

    def test_config_loading_valid_file(self):
        """Test loading valid configuration file."""
        config_manager = ConfigManager(self.valid_config_path)

        # Test that settings were loaded correctly
        self.assertEqual(config_manager.get_setting('monkey_type'), "Dart Monkey")
        self.assertEqual(config_manager.get_setting('monkey_coords'), (440, 355))
        self.assertEqual(config_manager.get_setting('selected_map'), "Monkey Meadow")
        self.assertEqual(config_manager.get_setting('confidence_threshold'), 0.85)

    def test_config_loading_invalid_file(self):
        """Test loading invalid configuration file."""
        # Should not raise exception, but should log warnings and use defaults
        config_manager = ConfigManager(self.invalid_config_path)

        # Should fall back to default settings since invalid config couldn't be loaded
        self.assertEqual(config_manager.get_setting('monkey_type'), "Dart Monkey")
        self.assertEqual(config_manager.get_setting('selected_map'), "Monkey Meadow")

    def test_config_loading_malformed_json(self):
        """Test loading malformed JSON configuration file."""
        # Should not raise exception, but should log error and use defaults
        config_manager = ConfigManager(self.malformed_config_path)

        # Should fall back to default settings
        self.assertEqual(config_manager.get_setting('monkey_type'), "Dart Monkey")

    def test_config_saving(self):
        """Test configuration saving functionality."""
        # Create a temporary config file path
        temp_config_path = os.path.join(self.temp_dir, 'test_save_config.json')

        # Create config manager and save
        config_manager = ConfigManager()
        success = config_manager.save_config(temp_config_path)

        self.assertTrue(success)
        self.assertTrue(os.path.exists(temp_config_path))

        # Verify the saved content
        with open(temp_config_path, 'r') as f:
            saved_data = json.load(f)

        self.assertEqual(saved_data['monkey_type'], "Dart Monkey")
        self.assertEqual(saved_data['monkey_coords'], [440, 355])
        self.assertEqual(saved_data['selected_map'], "Monkey Meadow")

    def test_config_loading_after_saving(self):
        """Test loading configuration that was previously saved."""
        # Save a config
        temp_config_path = os.path.join(self.temp_dir, 'test_roundtrip.json')
        original_config = ConfigManager()
        original_config.save_config(temp_config_path)

        # Load it back
        loaded_config = ConfigManager(temp_config_path)

        # Verify settings match
        self.assertEqual(
            original_config.get_setting('monkey_coords'),
            loaded_config.get_setting('monkey_coords')
        )
        self.assertEqual(
            original_config.get_setting('selected_map'),
            loaded_config.get_setting('selected_map')
        )

    def test_setting_updates(self):
        """Test individual setting updates."""
        config_manager = ConfigManager()

        # Update a valid setting
        success = config_manager.update_setting('monkey_type', 'Ninja Monkey')
        self.assertTrue(success)
        self.assertEqual(config_manager.get_setting('monkey_type'), 'Ninja Monkey')

        # Update coordinates (tuple conversion should work)
        success = config_manager.update_setting('monkey_coords', [500, 400])
        self.assertTrue(success)
        self.assertEqual(config_manager.get_setting('monkey_coords'), (500, 400))

        # Try to update non-existent setting
        success = config_manager.update_setting('nonexistent_setting', 'value')
        self.assertFalse(success)

        # Try to update with invalid key type
        success = config_manager.update_setting(123, 'value')  # Key should be string
        self.assertFalse(success)

    def test_coordinate_list_to_tuple_conversion(self):
        """Test conversion of coordinate lists to tuples."""
        config_manager = ConfigManager()

        # Test that lists get converted to tuples for coordinate fields
        success = config_manager.update_setting('monkey_coords', [600, 500])
        self.assertTrue(success)
        self.assertEqual(config_manager.get_setting('monkey_coords'), (600, 500))
        self.assertIsInstance(config_manager.get_setting('monkey_coords'), tuple)

        # Test that non-coordinate fields don't get converted
        success = config_manager.update_setting('monkey_type', 'Sniper Monkey')
        self.assertTrue(success)
        self.assertEqual(config_manager.get_setting('monkey_type'), 'Sniper Monkey')
        self.assertIsInstance(config_manager.get_setting('monkey_type'), str)

    def test_reset_to_defaults(self):
        """Test resetting configuration to default values."""
        config_manager = ConfigManager()

        # Modify some settings
        config_manager.update_setting('monkey_type', 'Modified Monkey')
        config_manager.update_setting('monkey_coords', (999, 999))

        # Verify modifications
        self.assertEqual(config_manager.get_setting('monkey_type'), 'Modified Monkey')
        self.assertEqual(config_manager.get_setting('monkey_coords'), (999, 999))

        # Reset to defaults
        config_manager.reset_to_defaults()

        # Verify reset
        self.assertEqual(config_manager.get_setting('monkey_type'), 'Dart Monkey')
        self.assertEqual(config_manager.get_setting('monkey_coords'), (440, 355))

    def test_get_setting_nonexistent(self):
        """Test getting non-existent setting returns None."""
        config_manager = ConfigManager()

        result = config_manager.get_setting('nonexistent_setting')
        self.assertIsNone(result)

    def test_config_directory_creation(self):
        """Test that config directory is created if it doesn't exist."""
        # Create a path in a non-existent directory
        nested_path = os.path.join(self.temp_dir, 'nested', 'deep', 'config.json')

        config_manager = ConfigManager()
        success = config_manager.save_config(nested_path)

        self.assertTrue(success)
        self.assertTrue(os.path.exists(nested_path))

        # Verify the directory structure was created
        self.assertTrue(os.path.exists(os.path.dirname(nested_path)))

    @patch('os.path.exists')
    def test_config_file_not_found_handling(self, mock_exists):
        """Test handling when config file doesn't exist."""
        mock_exists.return_value = False

        # Should not raise exception, should just use defaults
        config_manager = ConfigManager('/nonexistent/path/config.json')

        # Should have default settings
        self.assertEqual(config_manager.get_setting('monkey_type'), 'Dart Monkey')


class ConfigurationEdgeCaseTests(unittest.TestCase):
    """Test edge cases and error conditions for configuration."""

    def test_empty_config_file(self):
        """Test handling of empty config file."""
        temp_config_path = os.path.join(tempfile.mkdtemp(), 'empty_config.json')

        # Create empty file
        with open(temp_config_path, 'w') as f:
            f.write('')

        # Should handle gracefully and use defaults
        config_manager = ConfigManager(temp_config_path)
        self.assertEqual(config_manager.get_setting('monkey_type'), 'Dart Monkey')

        # Clean up
        os.remove(temp_config_path)
        os.rmdir(os.path.dirname(temp_config_path))

    def test_config_with_missing_fields(self):
        """Test config file with missing optional fields."""
        incomplete_config = {
            "monkey_type": "Dart Monkey",
            "monkey_coords": [440, 355],
            "monkey_key": "q"
            # Missing many other fields
        }

        temp_config_path = os.path.join(tempfile.mkdtemp(), 'incomplete_config.json')
        with open(temp_config_path, 'w') as f:
            json.dump(incomplete_config, f)

        # Should load successfully and use defaults for missing fields
        config_manager = ConfigManager(temp_config_path)

        # Should have specified values
        self.assertEqual(config_manager.get_setting('monkey_type'), 'Dart Monkey')
        self.assertEqual(config_manager.get_setting('monkey_coords'), (440, 355))

        # Should have defaults for missing values
        self.assertEqual(config_manager.get_setting('hero_type'), 'Quincy')
        self.assertEqual(config_manager.get_setting('selected_map'), 'Monkey Meadow')

        # Clean up
        os.remove(temp_config_path)
        os.rmdir(os.path.dirname(temp_config_path))

    def test_config_with_extra_fields(self):
        """Test config file with extra fields not in GameSettings."""
        config_with_extra = {
            "monkey_type": "Dart Monkey",
            "monkey_coords": [440, 355],
            "extra_field": "extra_value",
            "another_extra": 123
        }

        temp_config_path = os.path.join(tempfile.mkdtemp(), 'extra_config.json')
        with open(temp_config_path, 'w') as f:
            json.dump(config_with_extra, f)

        # Should load successfully and ignore extra fields
        config_manager = ConfigManager(temp_config_path)

        # Should have specified values
        self.assertEqual(config_manager.get_setting('monkey_type'), 'Dart Monkey')

        # Extra fields should not be accessible
        self.assertIsNone(config_manager.get_setting('extra_field'))

        # Clean up
        os.remove(temp_config_path)
        os.rmdir(os.path.dirname(temp_config_path))

    def test_concurrent_config_access(self):
        """Test thread safety of configuration access."""
        import threading
        import time

        config_manager = ConfigManager()

        results = []
        errors = []

        def access_config():
            try:
                for _ in range(100):
                    # Mix of read and write operations
                    config_manager.get_setting('monkey_type')
                    config_manager.update_setting('monkey_type', 'Dart Monkey')
                    results.append(True)
                    time.sleep(0.001)  # Small delay to encourage race conditions
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=access_config)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        self.assertEqual(len(errors), 0, f"Thread errors occurred: {errors}")
        self.assertEqual(len(results), 500)  # 5 threads * 100 operations each

    def test_config_file_permission_errors(self):
        """Test handling of file permission errors during save/load."""
        # This test is platform-dependent and may not work on all systems
        if os.name == 'nt':  # Windows
            self.skipTest("Permission testing not reliable on Windows")

        # Create a read-only directory for testing
        readonly_dir = os.path.join(tempfile.mkdtemp(), 'readonly')
        os.makedirs(readonly_dir)
        os.chmod(readonly_dir, 0o444)  # Read-only

        try:
            readonly_config_path = os.path.join(readonly_dir, 'readonly_config.json')

            config_manager = ConfigManager()
            # Should fail to save due to permissions
            success = config_manager.save_config(readonly_config_path)
            self.assertFalse(success)

        finally:
            # Restore permissions for cleanup
            os.chmod(readonly_dir, 0o755)
            os.rmdir(readonly_dir)


if __name__ == '__main__':
    unittest.main()
