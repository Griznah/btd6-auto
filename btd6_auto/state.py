# Shared state for BTD6 automation bot
# This module provides a mutable state object for cross-module flags


class SharedState:
    KILL_SWITCH = False


class DebugState:
    """Global debug state accessible across all modules"""
    DEBUG_ENABLED = False
