"""
Configuration management.
"""


# --- Windows-only Constants for MVP ---
MONKEY_TYPE = "Dart Monkey"
HERO_TYPE = "Quincy"

# Example coordinates (update for actual game window)
MONKEY_COORDS = (440, 355)
SELECT_MONKEY_COORDS = (1215, 145) # for debug purposes only
HERO_COORDS = (320, 250)
SELECT_HERO_COORDS = (1145, 145) # for debug purposes only
MONKEY_KEY = 'q'  # Key to select Dart Monkey
HERO_KEY = 'u'    # Key to select Hero

# Window title for BTD6 (Windows)
BTD6_WINDOW_TITLE = "BloonsTD6"

# Global killswitch flag
KILL_SWITCH = False

# Map selection (default: Monkey Meadow)
MAP_NAME = "Monkey Meadow"

# Difficulty selection (default: Easy)
DIFFICULTY = "Easy"  # Options: "Easy", "Medium", "Hard"

# Mode selection (default: Standard)
MODE = "Standard"  # Options: "Standard", "Alternate Bloons Rounds", etc.

def load_config(config_path):
    pass

def save_config(config, config_path):
    pass
