"""
Configuration loader for BTD6 automation bot.
Loads and validates map-specific and global configuration files.
Ensures compatibility with Windows file conventions.
"""
import os
import json
from typing import Any, Dict

CONFIGS_DIR = os.path.join(os.path.dirname(__file__), 'configs')
MAPS_DIR = os.path.join(CONFIGS_DIR, 'maps')
GLOBAL_CONFIG_PATH = os.path.join(CONFIGS_DIR, 'global.json')

class ConfigLoader:
    @staticmethod
    def load_global_config() -> Dict[str, Any]:
        """
        Load the global configuration from the module's GLOBAL_CONFIG_PATH.
        
        Returns:
            Dict[str, Any]: Parsed JSON content of the global configuration.
        
        Raises:
            FileNotFoundError: If the global configuration file does not exist.
            json.JSONDecodeError: If the file contains invalid JSON.
        """
        with open(GLOBAL_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
        """  
        Load global configuration from global.json.  
        Returns:  
            Dict[str, Any]: Global configuration dictionary.  
        Raises:  
            FileNotFoundError: If global.json is missing.  
            json.JSONDecodeError: If global.json is malformed.  
        """
    @staticmethod
    def load_map_config(map_name: str) -> Dict[str, Any]:
        """
        Load a map-specific configuration by name.
        
        Parameters:
            map_name (str): Map filename without extension; on Linux/macOS the case must match the filename.
        
        Returns:
            Dict[str, Any]: Parsed JSON configuration for the specified map.
        
        Raises:
            FileNotFoundError: If configs/maps/{map_name}.json does not exist.
            json.JSONDecodeError: If the map configuration file contains invalid JSON.
        """
        # Windows filenames are case-insensitive, but we use the exact name for clarity
        filename = f"{map_name}.json"
        path = os.path.join(MAPS_DIR, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Map config not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def validate_config(config: Dict[str, Any], required_fields: list) -> bool:
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

# Example usage:
# global_config = ConfigLoader.load_global_config()
# map_config = ConfigLoader.load_map_config('Monkey Meadow')
# ConfigLoader.validate_config(map_config, ["map_name", "hero", "actions"])