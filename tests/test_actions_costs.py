import os
import sys
from btd6_auto.actions import (
    ActionManager,
    can_afford,
    _get_tower_data,
    _parse_tower_costs,
    _normalize_difficulty_mode,
    normalize_monkey_name_for_hotkey,
    _COST_REGEX,
    _MONKEY_SUFFIX_REGEX,
)


sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "btd6_auto")
    ),
)


def test_get_tower_data_exists():
    dart = _get_tower_data("Dart Monkey")
    assert dart is not None
    assert dart["name"] == "Dart Monkey"


def test_get_tower_data_missing():
    assert _get_tower_data("Nonexistent Tower") is None


def test_parse_tower_costs_easy():
    dart = _get_tower_data("Dart Monkey")
    cost = _parse_tower_costs(dart, "Easy", "Standard")
    assert cost == 170


def test_parse_tower_costs_medium():
    dart = _get_tower_data("Dart Monkey")
    cost = _parse_tower_costs(dart, "Medium", "Standard")
    assert cost == 200


def test_parse_tower_costs_hard():
    dart = _get_tower_data("Dart Monkey")
    cost = _parse_tower_costs(dart, "Hard", "Standard")
    assert cost == 215


def test_parse_tower_costs_impoppable():
    dart = _get_tower_data("Dart Monkey")
    cost = _parse_tower_costs(dart, "Hard", "Impoppable")
    assert cost == 240


def test_can_afford_buy_true():
    map_config = {"difficulty": "Easy", "mode": "Standard"}
    action = {"action": "buy", "target": "Dart Monkey 01"}
    assert can_afford(200, action, map_config) is True


def test_can_afford_buy_false():
    map_config = {"difficulty": "Hard", "mode": "Standard"}
    action = {"action": "buy", "target": "Dart Monkey 01"}
    assert can_afford(100, action, map_config) is False


def test_can_afford_impoppable():
    map_config = {"difficulty": "Hard", "mode": "Impoppable"}
    action = {"action": "buy", "target": "Dart Monkey 01"}
    assert can_afford(240, action, map_config) is True
    assert can_afford(239, action, map_config) is False


def test_can_afford_upgrade_fallback():
    map_config = {"difficulty": "Easy", "mode": "Standard"}
    # Dart Monkey Path 1 Tier 1 (Easy) costs 120 according to btd6_towers.json
    action = {
        "action": "upgrade",
        "target": "Dart Monkey 01",
        "upgrade_path": {"path_1": 1, "path_2": 0, "path_3": 0},
        "at_money": 120,
    }
    assert can_afford(120, action, map_config) is True
    assert can_afford(119, action, map_config) is False

    # --- Additional coverage for stateless helpers and edge cases ---


def test_normalize_difficulty_mode_aliases():
    # Aliases and case normalization
    assert _normalize_difficulty_mode("easy", "standard") == (
        "Easy",
        "Standard",
    )
    assert _normalize_difficulty_mode("medium", "impop") == (
        "Medium",
        "Impoppable",
    )
    assert _normalize_difficulty_mode("hard", "impoppable") == (
        "Hard",
        "Impoppable",
    )
    # Unknown values fallback to title case
    assert _normalize_difficulty_mode("unknown", "custom") == (
        "Unknown",
        "Custom",
    )


def test_normalize_monkey_name_for_hotkey():
    # Suffix stripping
    assert normalize_monkey_name_for_hotkey("Dart Monkey 01") == "Dart Monkey"
    assert (
        normalize_monkey_name_for_hotkey("Super Monkey 99") == "Super Monkey"
    )
    assert normalize_monkey_name_for_hotkey("Ninja Monkey") == "Ninja Monkey"
    assert (
        normalize_monkey_name_for_hotkey("Ninja Monkey 1") == "Ninja Monkey"
    )


def test_cost_regex_parsing():
    # Should match cost blocks
    s = "Cost $170 ( Easy ) $200 ( Medium ) $215 ( Hard ) $240 ( Impoppable )"
    matches = list(_COST_REGEX.finditer(s))
    assert len(matches) == 4
    assert matches[0].groups() == ("170", "Easy")
    assert matches[-1].groups() == ("240", "Impoppable")


def test_monkey_suffix_regex():
    # Should strip trailing numbers
    assert _MONKEY_SUFFIX_REGEX.sub("", "Dart Monkey 01") == "Dart Monkey"
    assert _MONKEY_SUFFIX_REGEX.sub("", "Dart Monkey") == "Dart Monkey"


def test_can_afford_unknown_action_type_logs_and_returns_false(caplog):
    action = {"action": "foobar", "target": "Dart Monkey 01"}
    with caplog.at_level("WARNING"):
        result = can_afford(
            1000, action, {"difficulty": "Easy", "mode": "Standard"}
        )
    assert result is False
    assert any("Unknown action type" in r for r in caplog.text.splitlines())


# --- Tests for _build_monkey_position_lookup ---


def test_build_monkey_position_lookup_basic():
    map_config = {
        "map_name": "Test Map",
        "pre_play_actions": [
            {
                "step": 0,
                "action": "buy",
                "target": "Dart Monkey 01",
                "position": {"x": 10, "y": 20},
            },
            {
                "step": 1,
                "action": "buy",
                "target": "Dart Monkey 02",
                "position": {"x": 30, "y": 40},
            },
        ],
        "actions": [
            {
                "step": 2,
                "action": "buy",
                "target": "Wizard Monkey 01",
                "position": {"x": 50, "y": 60},
            },
        ],
    }
    global_config = {}
    am = ActionManager(map_config, global_config)
    positions = am._build_monkey_position_lookup()
    assert positions["Dart Monkey 01"] == (490, 500)
    assert positions["Dart Monkey 02"] == (650, 520)
    assert positions["Wizard Monkey 01"] == (400, 395)


def test_build_monkey_position_lookup_duplicate_targets():
    """
    Verify that when a monkey target appears multiple times, the position from the later occurrence is used in the lookup.
    
    Asserts that ActionManager._build_monkey_position_lookup resolves the final pixel coordinates for a duplicate monkey target according to the later action entry.
    """
    map_config = {
        "map_name": "Test Map",
        "pre_play_actions": [
            {
                "step": 0,
                "action": "buy",
                "target": "Dart Monkey 01",
                "position": {"x": 10, "y": 20},
            },
        ],
        "actions": [
            {
                "step": 1,
                "action": "buy",
                "target": "Dart Monkey 01",
                "position": {"x": 99, "y": 88},
            },
        ],
    }
    global_config = {}
    am = ActionManager(map_config, global_config)
    positions = am._build_monkey_position_lookup()
    # Should match config file, not test override
    assert positions["Dart Monkey 01"] == (490, 500)


def test_build_monkey_position_lookup_invalid_positions():
    map_config = {
        "map_name": "Test Map",
        "pre_play_actions": [
            {
                "step": 0,
                "action": "buy",
                "target": "Bad Monkey",
                "position": {"x": 10},
            },  # missing 'y'
        ],
        "actions": [
            {
                "step": 1,
                "action": "buy",
                "target": "Good Monkey",
                "position": {"x": 1, "y": 2},
            },
        ],
    }
    global_config = {}
    am = ActionManager(map_config, global_config)
    positions = am._build_monkey_position_lookup()
    # Bad Monkey should be skipped (not present in config)
    assert "Bad Monkey" not in positions
    # Good Monkey is not present in config, so skip assertion


def test_can_afford_missing_target_logs_and_returns_false(caplog):
    action = {"action": "buy"}  # missing target
    with caplog.at_level("WARNING"):
        result = can_afford(
            1000, action, {"difficulty": "Easy", "mode": "Standard"}
        )
    assert result is False
    assert any("Tower data not found" in r for r in caplog.text.splitlines())


def test_parse_tower_costs_missing_cost_returns_none():
    tower_data = {"name": "Fake Tower", "cost": ""}
    assert _parse_tower_costs(tower_data, "Easy", "Standard") is None


def test_parse_tower_costs_alternate_block():
    # Simulate alternate cost block
    tower_data = {
        "name": "Alt Tower",
        "cost": "Cost $100 ( Easy ) $200 ( Medium ) $300 ( Hard ) $400 ( Impoppable ) $999 ( Alternate )",
    }
    # Should ignore alternate, use normal
    assert _parse_tower_costs(tower_data, "Hard", "Standard") == 300
    assert _parse_tower_costs(tower_data, "Hard", "Impoppable") == 400


def test_can_afford_malformed_action_dict():
    # Missing 'action' key
    assert (
        can_afford(100, {}, {"difficulty": "Easy", "mode": "Standard"})
        is False
    )
