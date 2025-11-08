"""
Monkey hotkey lookup for BTD6 automation bot.

This module provides a helper to load and cache hotkeys for all monkeys from
data/btd6_towers.json. Use get_monkey_hotkey(monkey_name) to retrieve the hotkey
for a given monkey by display name. This replaces previous config-based hotkey lookup.

Usage:
    from btd6_auto.monkey_hotkey import get_monkey_hotkey
    hotkey = get_monkey_hotkey("Dart Monkey")

Notes:
    - Hotkeys are loaded from btd6_towers.json, which must contain a 'hotkey' field for each monkey.
    - If a monkey is missing or has no hotkey, the default is 'q' (configurable).
    - The cache is loaded once per process for efficiency.
"""

import os
from importlib import resources
import json
from typing import Dict, Optional

_TOWER_DATA_PACKAGE = "btd6_auto.data"
_TOWER_DATA_NAME = "btd6_towers.json"
_hotkey_cache: Optional[Dict[str, str]] = None


def _load_hotkey_cache() -> Dict[str, str]:
    """
    Load and cache monkey hotkeys from btd6_towers.json.
    Returns:
        Dict[str, str]: Mapping from monkey display name to hotkey.
    """
    global _hotkey_cache
    if _hotkey_cache is not None:
        return _hotkey_cache
    try:
        with (
            resources.files(_TOWER_DATA_PACKAGE)
            .joinpath(_TOWER_DATA_NAME)
            .open("r", encoding="utf-8") as f
        ):
            data = json.load(f)
    except (FileNotFoundError, ModuleNotFoundError):
        # Fallback for non-packaged runs
        legacy = os.path.join(
            os.path.dirname(__file__), "..", "data", _TOWER_DATA_NAME
        )
        with open(legacy, "r", encoding="utf-8") as f:
            data = json.load(f)
    cache = {}
    for category in data.values():
        for monkey, info in category.items():
            name = info.get("name", monkey)
            hotkey = info.get("hotkey")
            # Defensive normalization: ensure single lowercase char
            if isinstance(hotkey, str) and hotkey:
                cache[name] = hotkey.strip()[0].lower()
    _hotkey_cache = cache
    return cache


def get_monkey_hotkey(monkey_name: str, default: str = "q") -> str:
    """
    Get the hotkey for a monkey by display name.
    Args:
        monkey_name (str): The display name of the monkey (e.g., 'Dart Monkey').
        default (str): Default hotkey if not found.
    Returns:
        str: The hotkey for the monkey, or default if not found.
    """
    cache = _load_hotkey_cache()
    return cache.get(monkey_name, default)
