"""
Unit tests for btd6_auto.actions module and its integration in main automation flow.
"""

from unittest.mock import patch
from btd6_auto.actions import ActionManager, can_afford
import pytest
import logging

# Sample configs for testing
global_config = {
    "default_monkey_key": "q",
    "automation": {"logging_level": "INFO"},
}

map_config = {
    "hero": {
        "name": "Quincy",
        "hotkey": "u",
        "position": {"x": 100, "y": 200},
    },
    "pre_play_actions": [
        {
            "step": 0,
            "action": "buy",
            "target": "Dart Monkey 01",
            "position": {"x": 10, "y": 20},
            "hotkey": "q",
        },
        {
            "step": 1,
            "action": "buy",
            "target": "Dart Monkey 02",
            "position": {"x": 30, "y": 40},
            "hotkey": "q",
        },
    ],
    "actions": [
        {
            "step": 2,
            "at_money": 75,
            "action": "upgrade",
            "target": "Dart Monkey 01",
            "upgrade_path": "0-0-1",
        },
        {
            "step": 3,
            "at_money": 210,
            "action": "buy",
            "target": "Wizard Monkey 01",
            "position": {"x": 50, "y": 60},
        },
    ],
    "timing": {"placement_delay": 0.01, "upgrade_delay": 0.01},
}


def test_monkey_position_lookup():
    from btd6_auto.config_loader import ConfigLoader

    real_map_config = ConfigLoader.load_map_config("Monkey Meadow")
    am = ActionManager(real_map_config, global_config)
    # Dart Monkey 01 and Dart Monkey 02 positions from Monkey Meadow config
    assert am.get_monkey_position("Dart Monkey 01") == (490, 500)
    assert am.get_monkey_position("Dart Monkey 02") == (650, 520)
    assert am.get_monkey_position("Wizard Monkey 01") == (400, 395)
    assert am.get_monkey_position("Nonexistent") is None


def test_get_next_action_and_mark_completed():
    am = ActionManager(map_config, global_config)
    assert am.get_next_action()["step"] == 2
    am.mark_completed(2)
    assert am.get_next_action()["step"] == 3
    am.mark_completed(3)
    assert am.get_next_action() is None


def test_steps_remaining():
    am = ActionManager(map_config, global_config)
    assert am.steps_remaining() == 2
    am.mark_completed(2)
    assert am.steps_remaining() == 1
    am.mark_completed(3)
    assert am.steps_remaining() == 0


def test_can_afford():
    action = {"at_money": 100}
    assert can_afford(150, action)
    assert not can_afford(50, action)
    assert can_afford(100, action)
    # No at_money key
    assert can_afford(0, {"action": "buy"})


@patch("btd6_auto.actions.place_hero")
@patch("btd6_auto.actions.place_monkey")
def test_run_pre_play(mock_place_monkey, mock_place_hero):
    am = ActionManager(map_config, global_config)
    am.run_pre_play()
    mock_place_hero.assert_called_once_with((100, 200), "u")
    assert mock_place_monkey.call_count == 2
    mock_place_monkey.assert_any_call((10, 20), "q")
    mock_place_monkey.assert_any_call((30, 40), "q")


@patch("btd6_auto.actions.place_monkey")
def test_run_buy_action(mock_place_monkey):
    am = ActionManager(map_config, global_config)
    buy_action = {
        "step": 3,
        "action": "buy",
        "target": "Wizard Monkey 01",
        "position": {"x": 50, "y": 60},
    }
    am.run_buy_action(buy_action)
    # After refactor, Wizard Monkey 01 should resolve to 'Wizard Monkey' hotkey, which is 'a'
    mock_place_monkey.assert_called_once_with((50, 60), "a")


@patch("time.sleep", return_value=None)
def test_run_upgrade_action(mock_sleep):
    am = ActionManager(map_config, global_config)
    upgrade_action = {
        "step": 2,
        "action": "upgrade",
        "target": "Dart Monkey 01",
        "upgrade_path": "0-0-1",
    }
    # Just check it logs and sleeps, no error
    am.run_upgrade_action(upgrade_action)


# --- Additional coverage improvements ---
def test_invalid_position_raises_value_error():
    """
    Test that invalid hero or monkey positions raise ValueError.
    """
    bad_map_config = {
        "hero": {
            "name": "Quincy",
            "hotkey": "u",
            "position": {"x": 100},
        },  # missing 'y'
        "pre_play_actions": [
            {
                "step": 0,
                "action": "buy",
                "target": "Dart Monkey 01",
                "position": [10],
            },  # invalid tuple
        ],
        "actions": [],
        "timing": {"placement_delay": 0.01},
    }
    am = ActionManager(bad_map_config, global_config)
    # Hero position error
    with pytest.raises(ValueError):
        am.run_pre_play()
    # Monkey position error
    bad_map_config2 = {
        "hero": {
            "name": "Quincy",
            "hotkey": "u",
            "position": {"x": 100, "y": 200},
        },
        "pre_play_actions": [
            {
                "step": 0,
                "action": "buy",
                "target": "Dart Monkey 01",
                "position": [10],
            },  # invalid tuple
        ],
        "actions": [],
        "timing": {"placement_delay": 0.01},
    }
    am2 = ActionManager(bad_map_config2, global_config)
    with pytest.raises(ValueError):
        am2.run_pre_play()


@patch("btd6_auto.actions.place_hero", return_value=None)
@patch("btd6_auto.actions.place_monkey", return_value=None)
def test_placement_result_logging(mock_place_monkey, mock_place_hero, caplog):
    """
    Test that placement result logging does not warn for None return values.
    """
    am = ActionManager(map_config, global_config)
    with caplog.at_level(logging.WARNING):
        am.run_pre_play()
    # Should NOT log warnings for None, only for False
    # Should NOT log warnings for None, only for False
    assert not any(
        "hero placement returned False" in r for r in caplog.text.splitlines()
    )
    assert not any(
        "monkey placement returned False" in r
        for r in caplog.text.splitlines()
    )


def test_action_manager_empty_and_duplicate_steps():
    """
    Test ActionManager behavior with empty and duplicate step configs.
    """
    empty_config = {"pre_play_actions": [], "actions": []}
    am = ActionManager(empty_config, global_config)
    assert am.get_next_action() is None
    assert am.steps_remaining() == 0
    # Duplicate steps
    dup_config = {
        "pre_play_actions": [],
        "actions": [
            {
                "step": 1,
                "action": "buy",
                "target": "A",
                "position": {"x": 1, "y": 2},
            },
            {
                "step": 1,
                "action": "buy",
                "target": "B",
                "position": {"x": 3, "y": 4},
            },
        ],
    }
    am2 = ActionManager(dup_config, global_config)
    # Should return the first not completed (lowest step)
    assert am2.get_next_action()["target"] in ["A", "B"]


# --- Integration test for action manager orchestration logic ---
@patch("btd6_auto.actions.place_monkey")
@patch("btd6_auto.actions.place_hero")
def test_action_manager_integration(mock_place_hero, mock_place_monkey):
    """
    Integration test for ActionManager orchestration and currency logic.
    """
    # Simulate currency values for pre-play and main actions
    currency_values = [0, 100, 100, 250, 250, 250]
    currency_iter = iter(currency_values)

    def fake_get_currency():
        return next(currency_iter, 250)

    am = ActionManager(map_config, global_config)
    # Run pre-play actions
    am.run_pre_play()
    mock_place_hero.assert_called_once_with((100, 200), "u")
    assert mock_place_monkey.call_count == 2
    # Main action loop (simulate main.py logic)
    steps_done = 0
    while True:
        next_action = am.get_next_action()
        if not next_action:
            break
        currency = fake_get_currency()
        if not can_afford(currency, next_action):
            continue
        if next_action["action"] == "buy":
            am.run_buy_action(next_action)
        elif next_action["action"] == "upgrade":
            am.run_upgrade_action(next_action)
        am.mark_completed(next_action["step"])
        steps_done += 1
    # Should have completed all steps
    assert steps_done == 2
    assert mock_place_monkey.call_count == 3  # 2 pre-play + 1 buy
