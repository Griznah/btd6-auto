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
        with open(GLOBAL_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def load_map_config(map_name: str) -> Dict[str, Any]:
        # Windows filenames are case-insensitive, but we use the exact name for clarity
        filename = f"{map_name}.json"
        path = os.path.join(MAPS_DIR, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Map config not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def validate_config(config: Dict[str, Any], required_fields: list) -> bool:
        missing = [field for field in required_fields if field not in config]
        if missing:
            raise ValueError(f"Missing required config fields: {missing}")
        return True

# Example usage:
# global_config = ConfigLoader.load_global_config()
# map_config = ConfigLoader.load_map_config('Monkey Meadow')
# ConfigLoader.validate_config(map_config, ["map_name", "hero", "actions"])
