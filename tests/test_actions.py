"""
Unit tests for btd6_auto.actions module.
Tests ActionManager, can_afford, and helper functions using pytest and patching.
Uses 'Test Map' config for integration-like tests.
"""

# --- Imports (PEP8: all at top) ---
import logging
import pytest
from unittest.mock import patch
from btd6_auto.actions import ActionManager, can_afford
from btd6_auto import actions as actions_mod

# --- Shared configs for all tests ---
global_config = {
    "default_monkey_key": "q",
    "automation": {
        "logging_level": "INFO",
        "timing": {"placement_delay": 0.01, "upgrade_delay": 0.01},
    },
}

map_config = {
    "map_name": "Test Map",
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
            "upgrade_path": {"path_1": 0, "path_2": 0, "path_3": 1},
        },
        {
            "step": 3,
            "at_money": 210,
            "action": "buy",
            "target": "Wizard Monkey 01",
            "position": {"x": 50, "y": 60},
        },
    ],
    # timing removed; now in global_config
}


def test_monkey_position_lookup():
    """
    Test monkey position lookup using real map config from Test Map.
    Ensures correct (x, y) positions are returned for known monkeys and None for unknown.
    """
    from btd6_auto.config_loader import ConfigLoader

    real_map_config = ConfigLoader.load_map_config("Test Map")
    am = ActionManager(real_map_config, global_config)
    assert am.get_monkey_position("Dart Monkey 01") == (490, 500)
    assert am.get_monkey_position("Dart Monkey 02") == (650, 520)
    assert am.get_monkey_position("Wizard Monkey 01") == (400, 395)
    assert am.get_monkey_position("Nonexistent") is None


def test_get_next_action_and_mark_completed():
    """
    Test ActionManager get_next_action and mark_completed logic.
    Ensures correct step progression and None when all steps are completed.
    """
    am = ActionManager(map_config, global_config)
    assert am.get_next_action()["step"] == 2
    am.mark_completed(2)
    assert am.get_next_action()["step"] == 3
    am.mark_completed(3)
    assert am.get_next_action() is None


def test_steps_remaining():
    """
    Test ActionManager steps_remaining method for correct decrementing as steps are completed.
    """
    am = ActionManager(map_config, global_config)
    assert am.steps_remaining() == 2
    am.mark_completed(2)
    assert am.steps_remaining() == 1
    am.mark_completed(3)
    assert am.steps_remaining() == 0


def test_can_afford():
    """
    Test can_afford for buy and upgrade actions with various currency values.
    Checks both affordable and unaffordable scenarios.
    """
    buy_action = {"action": "buy", "target": "Dart Monkey 01"}
    upgrade_action = {
        "action": "upgrade",
        "target": "Dart Monkey 01",
        "upgrade_path": {"path_3": 1},
    }
    assert can_afford(250, buy_action, map_config)
    assert not can_afford(50, buy_action, map_config)
    assert can_afford(215, buy_action, map_config)
    assert can_afford(0, upgrade_action, map_config) is False


@patch("btd6_auto.actions.place_hero")
@patch("btd6_auto.actions.place_monkey")
def test_run_pre_play(mock_place_monkey, mock_place_hero):
    """
    Test ActionManager.run_pre_play to ensure hero and pre-play monkeys are placed correctly.
    Verifies correct calls to place_hero and place_monkey.
    """
    am = ActionManager(map_config, global_config)
    am.run_pre_play()
    mock_place_hero.assert_called_once_with((100, 200), "u")
    assert mock_place_monkey.call_count == 2
    mock_place_monkey.assert_any_call((10, 20), "q")
    mock_place_monkey.assert_any_call((30, 40), "q")


@patch("btd6_auto.actions.place_monkey")
def test_run_buy_action(mock_place_monkey):
    """
    Test ActionManager.run_buy_action for correct monkey placement and hotkey resolution.
    """
    am = ActionManager(map_config, global_config)
    buy_action = {
        "step": 3,
        "action": "buy",
        "target": "Wizard Monkey 01",
        "position": {"x": 50, "y": 60},
    }
    am.run_buy_action(buy_action)
    mock_place_monkey.assert_called_once_with((50, 60), "a")


@patch("time.sleep", return_value=None)
def test_run_upgrade_action(mock_sleep):
    """
    Test ActionManager.run_upgrade_action for upgrade logic and error-free execution.
    """
    am = ActionManager(map_config, global_config)
    upgrade_action = {
        "step": 2,
        "action": "upgrade",
        "target": "Dart Monkey 01",
        "upgrade_path": {"path_3": 1},
    }
    am.run_upgrade_action(upgrade_action)


@patch("btd6_auto.actions.place_hero", return_value=None)
@patch("btd6_auto.actions.place_monkey", return_value=None)
def test_placement_result_logging(mock_place_monkey, mock_place_hero, caplog):
    """
    Test that placement result logging does not warn for None return values.
    Only warns for explicit False returns.
    """
    am = ActionManager(map_config, global_config)
    with caplog.at_level(logging.WARNING):
        am.run_pre_play()
    assert not any("hero placement returned False" in r for r in caplog.text.splitlines())
    assert not any("monkey placement returned False" in r for r in caplog.text.splitlines())


def test_action_manager_empty_and_duplicate_steps():
    """
    Test ActionManager behavior with empty and duplicate step configs.
    Ensures correct handling of no actions and duplicate step numbers.
    """
    empty_config = {
        "map_name": "Test Map",
        "pre_play_actions": [],
        "actions": [],
    }
    am = ActionManager(empty_config, global_config)
    assert am.get_next_action() is None
    assert am.steps_remaining() == 0
    # Duplicate steps
    dup_config = {
        "map_name": "Test Map",
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
    Simulates currency changes and ensures all steps are completed as expected.
    """
    currency_values = [0, 100, 100, 250, 250, 250]
    currency_iter = iter(currency_values)

    def fake_get_currency():
        return next(currency_iter, 250)

    am = ActionManager(map_config, global_config)
    am.run_pre_play()
    mock_place_hero.assert_called_once_with((100, 200), "u")
    assert mock_place_monkey.call_count == 2
    steps_done = 0
    while True:
        next_action = am.get_next_action()
        if not next_action:
            break
        currency = fake_get_currency()
        if not can_afford(currency, next_action, map_config):
            continue
        if next_action["action"] == "buy":
            am.run_buy_action(next_action)
        elif next_action["action"] == "upgrade":
            am.run_upgrade_action(next_action)
        am.mark_completed(next_action["step"])
        steps_done += 1
    assert steps_done == 2
    assert mock_place_monkey.call_count == 3  # 2 pre-play + 1 buy


@pytest.mark.parametrize(
    "difficulty,mode,expected",
    [
        ("Easy", "Standard", ("Easy", "Standard")),
        ("easy", "impop", ("Easy", "Impoppable")),
        ("HARD", "std", ("Hard", "Standard")),
        ("Medium", "unknown", ("Medium", "Unknown")),
    ],
)
def test_normalize_difficulty_mode(difficulty, mode, expected):
    """
    Test normalization of difficulty and mode strings to canonical labels.
    """
    assert actions_mod._normalize_difficulty_mode(difficulty, mode) == expected


def test_normalize_monkey_name_for_hotkey():
    """
    Test normalization of monkey names for hotkey lookup.
    """
    assert actions_mod.normalize_monkey_name_for_hotkey("Dart Monkey 01") == "Dart Monkey"
    assert actions_mod.normalize_monkey_name_for_hotkey("Sniper Monkey 2") == "Sniper Monkey"
    assert actions_mod.normalize_monkey_name_for_hotkey("Alchemist") == "Alchemist"


@pytest.mark.parametrize(
    "current_money,action,map_config,expected",
    [
        (
            1000,
            {"action": "buy", "target": "Dart Monkey 01"},
            {"difficulty": "Easy", "mode": "Standard"},
            True,
        ),
        (
            10,
            {"action": "buy", "target": "Dart Monkey 01"},
            {"difficulty": "Easy", "mode": "Standard"},
            False,
        ),
        (
            1000,
            {"action": "upgrade", "target": "Dart Monkey 01", "upgrade_path": {"path_1": 1}},
            {"difficulty": "Easy", "mode": "Standard"},
            True,
        ),
        (
            1,
            {"action": "upgrade", "target": "Dart Monkey 01", "upgrade_path": {"path_1": 1}},
            {"difficulty": "Easy", "mode": "Standard"},
            False,
        ),
    ],
)
def test_can_afford_helpers(current_money, action, map_config, expected):
    """
    Test can_afford helper for buy and upgrade actions with mocked tower data and costs.
    Covers both affordable and unaffordable cases.
    """
    with (
        patch(
            "btd6_auto.actions._get_tower_data",
            return_value={
                "cost": "$170 ( Easy ) $200 ( Medium ) $215 ( Hard ) $240 ( Impoppable )",
                "upgrade_paths": {"Path 1": [{"costs": [100, 120, 140, 160]}]},
            },
        ),
        patch("btd6_auto.actions._parse_tower_costs", return_value=170),
        patch("btd6_auto.actions._get_upgrade_cost", return_value=100),
    ):
        assert actions_mod.can_afford(current_money, action, map_config) == expected


def test_parse_tower_costs():
    """
    Test parsing of tower cost strings for all supported difficulties and modes.
    """
    tower_data = {"cost": "$170 ( Easy ) $200 ( Medium ) $215 ( Hard ) $240 ( Impoppable )"}
    assert actions_mod._parse_tower_costs(tower_data, "Easy", "Standard") == 170
    assert actions_mod._parse_tower_costs(tower_data, "Medium", "Standard") == 200
    assert actions_mod._parse_tower_costs(tower_data, "Hard", "Standard") == 215
    assert actions_mod._parse_tower_costs(tower_data, "Hard", "Impoppable") == 240
    assert actions_mod._parse_tower_costs(tower_data, "Unknown", "Standard") == 200


def test_get_upgrade_cost():
    """
    Test extraction of upgrade costs for various paths, tiers, and difficulties.
    Covers valid and out-of-bounds cases.
    """
    tower_data = {
        "upgrade_paths": {
            "Path 1": [
                {"costs": [100, 120, 140, 160]},
                {"costs": [200, 220, 240, 260]},
            ]
        }
    }
    assert actions_mod._get_upgrade_cost(tower_data, 1, 0, "Easy", "Standard") == 100
    assert actions_mod._get_upgrade_cost(tower_data, 1, 1, "Medium", "Standard") == 220
    assert actions_mod._get_upgrade_cost(tower_data, 1, 0, "Hard", "Impoppable") == 160
    assert actions_mod._get_upgrade_cost(tower_data, 1, 5, "Easy", "Standard") is None
    assert actions_mod._get_upgrade_cost(tower_data, 2, 0, "Easy", "Standard") is None
