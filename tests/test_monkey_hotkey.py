"""
Unit tests for monkey_hotkey.py hotkey lookup.

This module tests the hotkey lookup logic for monkeys in BTD6.
It covers known and unknown monkey names, as well as cache structure.
"""

from btd6_auto.monkey_hotkey import get_monkey_hotkey, _load_hotkey_cache


def test_hotkey_lookup_known():
    """
    Test that known monkeys return the correct hotkey.
    Dart Monkey, Boomerang Monkey, and Sniper Monkey are checked.
    """
    # Dart Monkey is always present and has hotkey 'q'
    assert get_monkey_hotkey("Dart Monkey") == "q"
    # Boomerang Monkey hotkey is 'w'
    assert get_monkey_hotkey("Boomerang Monkey") == "w"
    # Sniper Monkey hotkey is 'z'
    assert get_monkey_hotkey("Sniper Monkey") == "z"


def test_hotkey_lookup_unknown():
    """
    Test that unknown monkey names return the default hotkey value.
    Checks both the default and a custom default value.
    """
    # Unknown monkey returns default
    assert get_monkey_hotkey("Fake Monkey") == "q"
    assert get_monkey_hotkey("Fake Monkey", default="x") == "x"


def test_hotkey_cache_structure():
    """
    Test the structure of the hotkey cache.
    Ensures required monkeys are present and all hotkeys are single-character strings.
    """
    cache = _load_hotkey_cache()
    # Should contain Dart Monkey and Boomerang Monkey
    assert "Dart Monkey" in cache
    assert "Boomerang Monkey" in cache
    # All values should be single-character strings
    for hotkey in cache.values():
        assert isinstance(hotkey, str)
        assert len(hotkey) == 1
