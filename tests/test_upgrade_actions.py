import pytest
from unittest.mock import patch
from btd6_auto.actions import ActionManager

"""
All tests in this module patch GUI/input helpers to prevent real mouse/keyboard actions.
This avoids side effects and CI failures when running tests that invoke run_upgrade_action.
"""


# Patch move_and_click, cursor_resting_spot, and keyboard.send for all tests
@pytest.fixture(autouse=True)
def patch_gui_input():
    with (
        patch("btd6_auto.input.move_and_click"),
        patch("btd6_auto.input.cursor_resting_spot", return_value=(0, 0)),
        patch("keyboard.send"),
    ):
        yield


class DummyGlobalConfig(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def make_manager(map_config=None, global_config=None):
    if map_config is None:
        map_config = {
            "map_name": "Monkey Meadow",
            "difficulty": "Easy",
            "mode": "Standard",
            "actions": [],
            "pre_play_actions": [],
            "hero": {},
        }
    if global_config is None:
        global_config = DummyGlobalConfig(
            {
                "hotkey": {
                    "upgrade_path_1": "a",
                    "upgrade_path_2": "s",
                    "upgrade_path_3": "d",
                },
                "automation": {"timing": {"upgrade_delay": 0}},
            }
        )
    return ActionManager(map_config, global_config)


def test_upgrade_action_tracks_state():
    """
    Test that upgrade actions correctly track and update the monkey's upgrade state.
    Scenario: Upgrade Dart Monkey 01 from tier 0 to 1, then from 1 to 2 on path_1.
    Expected outcome: State reflects the highest tier reached, and upgrades are not repeated.
    """
    manager = make_manager()
    manager.monkey_positions = {"Dart Monkey 01": (100, 100)}
    action1 = {
        "step": 1,
        "action": "upgrade",
        "target": "Dart Monkey 01",
        "upgrade_path": {"path_1": 1, "path_2": 0, "path_3": 0},
    }
    manager.run_upgrade_action(action1)
    assert manager.monkey_upgrade_state["Dart Monkey 01"]["path_1"] == 1
    action2 = {
        "step": 2,
        "action": "upgrade",
        "target": "Dart Monkey 01",
        "upgrade_path": {"path_1": 2, "path_2": 0, "path_3": 0},
    }
    manager.run_upgrade_action(action2)
    assert manager.monkey_upgrade_state["Dart Monkey 01"]["path_1"] == 2


def test_upgrade_action_skips_lower_tiers():
    """
    Test that upgrade actions do not downgrade monkey tiers.
    Scenario: Dart Monkey 01 is already at tier 2 on path_1, action requests tier 1.
    Expected outcome: State remains at tier 2, no downgrade occurs.
    """
    manager = make_manager()
    manager.monkey_positions = {"Dart Monkey 01": (100, 100)}
    manager.monkey_upgrade_state["Dart Monkey 01"] = {
        "path_1": 2,
        "path_2": 0,
        "path_3": 0,
    }
    action = {
        "step": 3,
        "action": "upgrade",
        "target": "Dart Monkey 01",
        "upgrade_path": {"path_1": 1, "path_2": 0, "path_3": 0},
    }
    manager.run_upgrade_action(action)
    assert manager.monkey_upgrade_state["Dart Monkey 01"]["path_1"] == 2


def test_upgrade_action_multiple_paths():
    """
    Test that upgrade actions correctly apply upgrades to multiple paths in one action.
    Scenario: Upgrade Dart Monkey 01 to tier 1 on path_1 and tier 2 on path_2 in a single action.
    Expected outcome: State reflects the correct tier for each path after the action.
    """
    manager = make_manager()
    manager.monkey_positions = {"Dart Monkey 01": (100, 100)}
    action = {
        "step": 4,
        "action": "upgrade",
        "target": "Dart Monkey 01",
        "upgrade_path": {"path_1": 1, "path_2": 2, "path_3": 0},
    }
    # Call repeatedly until all upgrades are applied (action marked completed)
    for _ in range(10):  # Prevent infinite loop
        manager.run_upgrade_action(action)
        state = manager.monkey_upgrade_state["Dart Monkey 01"]
        # Optionally, check intermediate state here if desired
        if action["step"] in manager.completed_steps:
            break
    state = manager.monkey_upgrade_state["Dart Monkey 01"]
    assert state["path_1"] == 1
    assert state["path_2"] == 2
    assert state["path_3"] == 0
