"""
Shared configuration utilities for BTD6 automation bot.
"""


def get_vision_config():
    """
    Load and return the vision configuration from the global config file.
    Returns:
        dict: Vision configuration dictionary.
    """
    import json
    import os

    config_path = os.path.join(
        os.path.dirname(__file__), "configs", "global.json"
    )
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config.get("vision", {})
    except Exception as e:
        # Log error if logging is available
        try:
            import logging

            logging.error(f"Failed to load vision config: {e}")
        except ImportError:
            pass
        return {}
