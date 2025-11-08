"""
Configuration loader for BTD6 automation bot.
Loads and validates map-specific and global configuration files.
Ensures compatibility with Windows file conventions.
"""

import os
import json
from typing import Dict, Any, Optional, ClassVar

CONFIGS_DIR = os.path.join(os.path.dirname(__file__), "configs")
MAPS_DIR = os.path.join(CONFIGS_DIR, "maps")
GLOBAL_CONFIG_PATH = os.path.join(CONFIGS_DIR, "global.json")


class ConfigLoader:
    """
    Configuration loader with caching for global config and map filename resolution.
    """

    _global_config_cache: ClassVar[Optional[Dict[str, Any]]] = None
    _display_to_filename_cache: ClassVar[Optional[Dict[str, str]]] = None

    @staticmethod
    def load_global_config() -> Dict[str, Any]:
        """
        Load the global configuration from the module's GLOBAL_CONFIG_PATH, using cache if available.
        Returns:
            Dict[str, Any]: Parsed JSON content of the global configuration.
        Raises:
            FileNotFoundError: If the global configuration file does not exist.
            json.JSONDecodeError: If the file contains invalid JSON.
        """
        if ConfigLoader._global_config_cache is None:
            with open(GLOBAL_CONFIG_PATH, "r", encoding="utf-8") as f:
                ConfigLoader._global_config_cache = json.load(f)
            # Invalidate display_to_filename cache if global config is reloaded
            ConfigLoader._display_to_filename_cache = None
        return ConfigLoader._global_config_cache

    @staticmethod
    def _normalize(name: str) -> str:
        """
        Normalize map display names for Windows compatibility (case/space insensitive).
        """
        return name.replace(" ", "").replace("'", "").lower()

    @staticmethod
    def get_map_filename(map_display_name: str) -> str:
        """
        Resolve the config filename for a given map display name using cached mapping.
        Parameters:
            map_display_name (str): The display name of the map (e.g., 'Monkey Meadow').
        Returns:
            str: The config filename (e.g., 'monkey_meadow.json').
        Raises:
            KeyError: If the map display name is not found in the mapping.
        """
        if ConfigLoader._display_to_filename_cache is None:
            global_config = ConfigLoader.load_global_config()
            ConfigLoader._display_to_filename_cache = {
                ConfigLoader._normalize(v): k
                for k, v in global_config.get("map_filenames", {}).items()
            }
        normalized_input = ConfigLoader._normalize(map_display_name)
        display_to_filename = ConfigLoader._display_to_filename_cache
        if normalized_input not in display_to_filename:
            raise KeyError(
                f"Map display name not found in config: {map_display_name}"
            )
        return display_to_filename[normalized_input]

    @staticmethod
    def load_map_config(map_display_name: str) -> Dict[str, Any]:
        """
        Load a map-specific configuration by display name using the cached mapping.
        Parameters:
            map_display_name (str): The display name of the map (e.g., 'Monkey Meadow').
        Returns:
            Dict[str, Any]: Parsed JSON configuration for the specified map.
        Raises:
            FileNotFoundError: If the map config file does not exist or map display name is not found.
            json.JSONDecodeError: If the map configuration file contains invalid JSON.
        """
        try:
            filename = ConfigLoader.get_map_filename(map_display_name)
        except KeyError as e:
            raise FileNotFoundError(
                f"Map config not found for display name: {map_display_name}"
            ) from e
        path = os.path.join(MAPS_DIR, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Map config not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def validate_config(
        config: Dict[str, Any], required_fields: list
    ) -> bool:
        """
        Validate that all required fields exist in the given configuration.
        Parameters:
            config (Dict[str, Any]): Configuration dictionary to check.
            required_fields (list): Sequence of field names that must be present in `config`.
        Returns:
            bool: `True` if all required fields are present.
        Raises:
            ValueError: If any required fields are missing; the exception message lists the missing fields.
        """
        missing = [field for field in required_fields if field not in config]
        if missing:
            raise ValueError(f"Missing required config fields: {missing}")
        return True

    @staticmethod
    def invalidate_cache() -> None:
        """
        Invalidate the global config and display-to-filename caches (for testing or reload).
        """
        ConfigLoader._global_config_cache = None
        ConfigLoader._display_to_filename_cache = None


# Example usage:
# global_config = ConfigLoader.load_global_config()
# map_config = ConfigLoader.load_map_config('Monkey Meadow')
# ConfigLoader.validate_config(map_config, ["map_name", "hero", "actions"])
