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
        # Note: Update this list when new maps are added to BTD6
        # Last updated: BTD6 v40.0 (as of 2024)
        valid_maps = [
            "Monkey Meadow", "Scrapyard", "Riverside", "Clover", "Sunken Columns",
            "Balance", "Encrypted", "Bazaar", "Adora's Temple", "Spring Spring",
            "KartsNDarts", "Moon Landing", "Haunted", "Downstream", "Firing Range",
            "Cracked", "Streambed", "Chutes", "Rake", "Spice Islands",
            "X Factor", "Mesa", "Geared", "Spillway", "Cargo", "Pat's Pond",
            "Peninsula", "High Finance", "Another Brick", "Off the Coast",
            "Cornfield", "Underground", "Sanctuary", "Ravine", "Flooded Valley",
            "Infernal", "Bloody Puddles", "Workshop", "Quad", "Dark Castle",
            "Muddy Puddles", "Ouch", "Dark Dungeons", "Bloody Puddles"
        ]

        valid_difficulties = ["Easy", "Medium", "Hard", "Impoppable"]
        valid_modes = ["Standard", "Primary Only", "Deflation", "Reverse", "Half Cash",
                      "Alternate Bloons Rounds", "Double HP MOABs", "CHIMPS", "Magic Only"]

        if self.selected_difficulty not in valid_difficulties:
            raise ValueError(f"Difficulty must be one of {valid_difficulties}")

        if self.selected_mode not in valid_modes:
            raise ValueError(f"Mode must be one of {valid_modes}")

        if self.selected_map not in valid_maps:
            raise ValueError(f"Map '{self.selected_map}' not available. Available maps: {valid_maps}")

        if not 0 < self.click_delay <= 5.0:
            raise ValueError("Click delay must be between 0 and 5 seconds")

        if self.confidence_threshold < 0.1 or self.confidence_threshold > 1.0:
            raise ValueError("Confidence threshold must be between 0.1 and 1.0")


    def convert_lists_to_tuples(self, key: str, value: Any) -> Any:
        """Convert coordinate lists back to tuples for specific keys.

        Args:
            key: The setting name to check
            value: The value to potentially convert

        Returns:
            The converted value (tuple if original was tuple, list if original was list)
        """
        # Only convert known coordinate fields to avoid unexpected conversions
        coordinate_fields = {'monkey_coords', 'hero_coords'}

        if key in coordinate_fields and isinstance(value, list):
            # Validate that this looks like coordinates before converting
            if len(value) == 2 and all(isinstance(x, int) for x in value):
                return tuple(value)
            # Invalid format, return as-is (caller can handle validation)

        return value
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

    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        return os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')

    def save_config(self, path: Optional[str] = None) -> bool:
        """Save current configuration to file.

        Args:
            path: Optional path to save configuration to. If None, uses default config path.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Determine target path
            target_path = path or self.config_path

            # Create parent directory if it doesn't exist
            parent_dir = os.path.dirname(target_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

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

            with open(target_path, 'w') as f:
                json.dump(config_data, f, indent=2)

            self.logger.info(f"Configuration saved to {target_path}")
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
                    converted_value = self.settings.convert_lists_to_tuples(key, value)
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
        if not isinstance(key, str):
            self.logger.error("Setting key must be a string")
            return False

        try:
            if hasattr(self.settings, key):
                old_value = getattr(self.settings, key)
                # Convert lists back to tuples for tuple-typed settings
                converted_value = self.settings.convert_lists_to_tuples(key, value)
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
            # Restore old value if it existed
            if 'old_value' in locals():
                setattr(self.settings, key, old_value)
            self.logger.error(f"Failed to update setting {key}: {e}")
            return False

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
class _ConfigProxy:
    """Proxy class that dynamically fetches current configuration values."""

    def __init__(self, config_manager):
        self._config = config_manager

    def __getattr__(self, name):
        """Dynamically get current setting value from config manager."""
        return self._config.get_setting(name)


def _get_config_manager():
    """Get or create global config manager instance."""
    if not hasattr(_get_config_manager, '_instance'):
        _get_config_manager._instance = ConfigManager()
    return _get_config_manager._instance


# Module-level accessors for backward compatibility
_config_manager = _get_config_manager()
_config_proxy = _ConfigProxy(_config_manager)

# These will now dynamically fetch current values

def __getattr__(name: str):
    """
    Module-level dynamic attribute access for settings.
    Allows: from btd6_auto.config import CLICK_DELAY
    """
    try:
        return getattr(_config_proxy, name)
    except AttributeError:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

def __dir__():
    """
    Module-level __dir__ for discoverability of settings and attributes.
    Returns sorted list of globals plus settings keys.
    """
    global_names = list(globals().keys())
    # Get all GameSettings fields
    settings_keys = list(_config_manager.settings.__dataclass_fields__.keys())
    return sorted(set(global_names + settings_keys))

