"""
Configuration management with validation and persistence.
"""

import json
import os
import logging
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class GameSettings:
    """Game configuration settings with validation."""
    # Monkey configuration
    monkey_type: str = "Dart Monkey"
    monkey_coords: Tuple[int, int] = (440, 355)
    monkey_key: str = 'q'

    # Hero configuration
    hero_type: str = "Quincy"
    hero_coords: Tuple[int, int] = (320, 250)
    hero_key: str = 'u'

    # Game settings
    window_title: str = "BloonsTD6"
    selected_map: str = "Monkey Meadow"
    selected_difficulty: str = "Easy"
    selected_mode: str = "Standard"

    # Timing settings
    click_delay: float = 0.2
    operation_timeout: float = 30.0

    # Advanced settings
    max_retries: int = 3
    retry_delay: float = 1.0
    confidence_threshold: float = 0.85

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_coordinates()
        self._validate_keys()
        self._validate_settings()

    def _validate_coordinates(self):
        """Validate all coordinate tuples."""
        coordinates = {
            'monkey_coords': self.monkey_coords,
            'hero_coords': self.hero_coords,
        }

        for name, coords in coordinates.items():
            if not isinstance(coords, tuple) or len(coords) != 2:
                raise ValueError(f"{name} must be a tuple of (x, y) coordinates")
            x, y = coords
            if not isinstance(x, int) or not isinstance(y, int):
                raise ValueError(f"{name} coordinates must be integers")
            if x < 0 or y < 0:
                raise ValueError(f"{name} coordinates must be non-negative")

    def _validate_keys(self):
        """Validate keyboard inputs."""
        keys = {
            'monkey_key': self.monkey_key,
            'hero_key': self.hero_key,
        }

        for name, key in keys.items():
            if not isinstance(key, str) or len(key) != 1:
                raise ValueError(f"{name} must be a single character string")

    def _validate_settings(self):
        """Validate game settings."""
        valid_difficulties = ["Easy", "Medium", "Hard"]
        valid_modes = ["Standard", "Alternate Bloons Rounds", "Half Cash", "Double HP MOABs"]
        valid_maps = ["Monkey Meadow", "Scrapyard", "Riverside", "Clover", "Sunken Columns"]

        if self.selected_difficulty not in valid_difficulties:
            raise ValueError(f"Difficulty must be one of {valid_difficulties}")

        if self.selected_mode not in valid_modes:
            raise ValueError(f"Mode must be one of {valid_modes}")

        if self.selected_map not in valid_maps:
            raise ValueError(f"Map must be one of {valid_maps}")

        if not 0 < self.click_delay <= 5.0:
            raise ValueError("Click delay must be between 0 and 5 seconds")

        if self.confidence_threshold < 0.1 or self.confidence_threshold > 1.0:
            raise ValueError("Confidence threshold must be between 0.1 and 1.0")


    def _convert_lists_to_tuples(self, key: str, value: Any) -> Any:
        """Convert lists back to tuples recursively when the existing setting is a tuple.

        Args:
            key: The setting name to check
            value: The value to potentially convert

        Returns:
            The converted value (tuple if original was tuple, list if original was list)
        """
        if not hasattr(self.settings, key):
            return value

        current = getattr(self.settings, key)

        # If the current setting is a tuple, convert lists back to tuples recursively
        if isinstance(current, tuple):
            if isinstance(value, list):
                # Convert list to tuple, handling nested structures
                return tuple(self._convert_element(elem) for elem in value)
            elif isinstance(value, tuple):
                # Already a tuple, but check if elements need conversion
                return tuple(self._convert_element(elem) for elem in value)

        return value

    def _convert_element(self, element: Any) -> Any:
        """Convert a single element recursively if it's a list that should be a tuple."""
        if isinstance(element, list):
            # Check if this list should be converted to tuple by looking at default values
            # For now, assume any 2-element list of integers should be a coordinate tuple
            if len(element) == 2 and all(isinstance(x, int) for x in element):
                return tuple(element)
            else:
                # For other lists, convert elements recursively
                return [self._convert_element(elem) for elem in element]
class ConfigManager:
    """Manages BTD6 automation configuration with validation and persistence."""

    def __init__(self, config_path: str = None):
        """Initialize configuration manager.

        Args:
            config_path: Path to configuration file. If None, uses default path.
        """
        self.config_path = config_path or self._get_default_config_path()
        self.settings = GameSettings()
        self.logger = logging.getLogger(__name__)

        # Load existing configuration if available
        if os.path.exists(self.config_path):
            self.load_config()

    def save_config(self) -> bool:
        """Save current configuration to file.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            config_data = {
                'monkey_type': self.settings.monkey_type,
                'monkey_coords': self.settings.monkey_coords,
                'monkey_key': self.settings.monkey_key,
                'hero_type': self.settings.hero_type,
                'hero_coords': self.settings.hero_coords,
                'hero_key': self.settings.hero_key,
                'window_title': self.settings.window_title,
                'selected_map': self.settings.selected_map,
                'selected_difficulty': self.settings.selected_difficulty,
                'selected_mode': self.settings.selected_mode,
                'click_delay': self.settings.click_delay,
                'operation_timeout': self.settings.operation_timeout,
                'max_retries': self.settings.max_retries,
                'retry_delay': self.settings.retry_delay,
                'confidence_threshold': self.settings.confidence_threshold,
            }

            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)

            self.logger.info(f"Configuration saved to {self.config_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False

    def load_config(self) -> bool:
        """Load configuration from file.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            if not os.path.exists(self.config_path):
                self.logger.warning(f"Configuration file not found: {self.config_path}")
                return False

            with open(self.config_path, 'r') as f:
                config_data = json.load(f)

            # Update settings with loaded values
            for key, value in config_data.items():
                if hasattr(self.settings, key):
                    # Convert lists back to tuples for tuple-typed settings
                    converted_value = self._convert_lists_to_tuples(key, value)
                    setattr(self.settings, key, converted_value)

            # Re-validate after loading
            self.settings._validate_coordinates()
            self.settings._validate_keys()
            self.settings._validate_settings()

            self.logger.info(f"Configuration loaded from {self.config_path}")
            return True

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in configuration file: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return False

    def update_setting(self, key: str, value: Any) -> bool:
        """Update a single configuration setting.

        Args:
            key: Setting name to update
            value: New value for the setting

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            if hasattr(self.settings, key):
                old_value = getattr(self.settings, key)
                # Convert lists back to tuples for tuple-typed settings
                converted_value = self._convert_lists_to_tuples(key, value)
                setattr(self.settings, key, converted_value)
                # Re-validate the specific setting
                if key.endswith('_coords'):
                    self.settings._validate_coordinates()
                elif key.endswith('_key'):
                    self.settings._validate_keys()
                else:
                    self.settings._validate_settings()

                self.logger.info(f"Updated setting {key} = {value}")
                return True
            else:
                self.logger.error(f"Unknown setting: {key}")
                return False
        except Exception as e:
            if 'old_value' in locals():
                setattr(self.settings, key, old_value)
            self.logger.error(f"Failed to update setting {key}: {e}")
            return False
        return getattr(self.settings, key, None)

    def get_setting(self, key: str) -> Any:
        """Get a configuration setting value.

        Args:
            key: Setting name to retrieve

        Returns:
            The setting value, or None if the setting doesn't exist
        """
        return getattr(self.settings, key, None)

    def reset_to_defaults(self):
        """Reset all settings to default values.
        """
        self.settings = GameSettings()
        self.logger.info("All settings reset to defaults")


# Global killswitch flag (keeping for backward compatibility)
KILL_SWITCH = False


# Backward compatibility: expose settings as module-level variables
def _get_config_manager():
    """Get or create global config manager instance.
    """
    if not hasattr(_get_config_manager, '_instance'):
        _get_config_manager._instance = ConfigManager()
    return _get_config_manager._instance


def load_config(config_path: str = None) -> bool:
    """Load configuration from file (backward compatibility).
    """
    return _get_config_manager().load_config()


def save_config(config_path: str = None) -> bool:
    """Save configuration to file (backward compatibility).
    """
    return _get_config_manager().save_config()


# Module-level accessors for backward compatibility
_config_manager = _get_config_manager()
MONKEY_TYPE = _config_manager.get_setting('monkey_type')
MONKEY_COORDS = _config_manager.get_setting('monkey_coords')
MONKEY_KEY = _config_manager.get_setting('monkey_key')
HERO_TYPE = _config_manager.get_setting('hero_type')
HERO_COORDS = _config_manager.get_setting('hero_coords')
HERO_KEY = _config_manager.get_setting('hero_key')
BTD6_WINDOW_TITLE = _config_manager.get_setting('window_title')
selected_map = _config_manager.get_setting('selected_map')
selected_difficulty = _config_manager.get_setting('selected_difficulty')
selected_mode = _config_manager.get_setting('selected_mode')
CLICK_DELAY = _config_manager.get_setting('click_delay')
