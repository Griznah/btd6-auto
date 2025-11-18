"""
Shared configuration utilities for BTD6 automation bot.
"""


def get_vision_config():
    """
    Load the vision configuration from the module's configs/global.json file.
    
    If the file is missing, unreadable, or contains invalid JSON, returns an empty dict and attempts to log the error.
    
    Returns:
        dict: The value of the top-level "vision" key from the configuration, or an empty dict if not present or on error.
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
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        PermissionError,
        OSError,
    ):
        # Log error if logging is available
        try:
            import logging

            logging.exception("Failed to load vision config")
        except ImportError:
            pass
        return {}