"""
Action management and execution for BTD6 automation routines.

This module defines the ActionManager class, which tracks and manages the current action list for a map run, provides lookup for monkey positions, and orchestrates execution of pre-play and buy actions. Low-level stateless helpers are kept as standalone functions for testability and clarity.

Classes:
    ActionManager: Manages actions and monkey positions for a BTD6 map run.

Functions:
    can_afford: Dummy check for action affordability.
"""

from typing import Any, Dict, Optional, Tuple
import json
import re
from functools import lru_cache
from pathlib import Path
import logging
import time
import keyboard

from btd6_auto.monkey_manager import place_monkey, place_hero
from btd6_auto.monkey_hotkey import get_monkey_hotkey
from btd6_auto.config_loader import get_tower_positions_for_map
from btd6_auto.input import click


# Compile regexes at module level
_COST_REGEX = re.compile(r"\$(\d+) \( ([^)]+) \)")
_MONKEY_SUFFIX_REGEX = re.compile(r"\s+\d+$")

# Aliases for normalization
_DIFFICULTY_ALIASES = {
    "easy": "Easy",
    "medium": "Medium",
    "hard": "Hard",
}
_MODE_ALIASES = {
    "standard": "Standard",
    "impop": "Impoppable",
    "impoppable": "Impoppable",
    "std": "Standard",
}


def _normalize_difficulty_mode(difficulty: str, mode: str) -> tuple[str, str]:
    """
    Normalize difficulty and mode input strings to canonical labels using module aliases.

    Strips whitespace and lowercases inputs, then maps them through internal alias dictionaries
    to produce standardized labels.

    Returns:
        tuple[str, str]: (normalized_difficulty, normalized_mode) where each element is the
        canonical label for the provided input.
    """
    d = difficulty.strip().lower()
    m = mode.strip().lower()
    norm_d = _DIFFICULTY_ALIASES.get(d, difficulty.title())
    norm_m = _MODE_ALIASES.get(m, mode.title())
    return norm_d, norm_m


@lru_cache(maxsize=1)
def _load_towers_json() -> Dict[str, Any]:
    """
    Load and return the BTD6 towers JSON data from the package data directory.

    Attempts to read and parse data/btd6_towers.json located two levels above this module; logs any IO or decode errors and returns an empty dict on failure.

    Returns:
        Dict[str, Any]: Parsed towers JSON mapping or an empty dict if the file cannot be read or parsed.
    """
    towers_path = Path(__file__).parent.parent / "data" / "btd6_towers.json"
    try:
        with towers_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logging.exception(f"Failed to load tower data: {e}")
        return {}


@lru_cache(maxsize=128)
def _get_tower_data(tower_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the tower data entry for a given tower name from the loaded towers JSON.

    Searches the cached towers data and returns the matching tower's data dictionary when present.

    Returns:
        dict | None: The tower's data dictionary if found, `None` otherwise.
    """
    towers_json = _load_towers_json()
    for category in towers_json.values():
        if tower_name in category:
            return category[tower_name]
    return None


def normalize_monkey_name_for_hotkey(monkey_name: str) -> str:
    """
    Normalize a monkey name by removing a trailing space and numeric suffix used for disambiguation.

    Parameters:
        monkey_name (str): Monkey name from configuration (e.g., "Dart Monkey 01").

    Returns:
        str: Monkey name with trailing numeric suffix removed and surrounding whitespace trimmed (e.g., "Dart Monkey").
    """
    normalized = re.sub(r"\s+\d+$", "", monkey_name)
    return normalized.strip()


class ActionManager:
    """
    Manages the list of actions for a BTD6 map run, including pre-play and main actions.
    Provides lookup for monkey positions and orchestrates action execution.

    Attributes:
        map_config (Dict[str, Any]): Map-specific configuration.
        global_config (Dict[str, Any]): Global configuration.
        actions (List[Dict[str, Any]]): Sorted list of main actions.
        pre_play_actions (List[Dict[str, Any]]): Sorted list of pre-play actions.
        hero (Dict[str, Any]): Hero configuration.
        monkey_positions (Dict[str, Tuple[int, int]]): Lookup for monkey positions.
        completed_steps (set): Steps that have been completed.
        timing (Dict[str, Any]): Timing configuration for delays.
    """

    def get_next_action(self) -> Optional[Dict[str, Any]]:
        """
        Selects the first action whose step is not marked as completed.

        Returns:
            dict: The next action dictionary, or `None` if no uncompleted actions remain.
        """
        for action in self.actions:
            if action.get("step") not in self.completed_steps:
                return action
        return None

    def _build_monkey_position_lookup(self) -> Dict[str, Tuple[int, int]]:
        """
        Construct a mapping from monkey/hero names to their (x, y) positions using config_loader's get_tower_positions_for_map.
        Returns:
            Dict[str, Tuple[int, int]]: Mapping from monkey/hero name to its (x, y) position.
        """

        map_name = self.map_config.get("map_name")
        if not map_name:
            raise ValueError(
                "Map name not found in config; position lookup will be empty"
            )
        return get_tower_positions_for_map(map_name)

    def _check_placement_result(self, result, target, pos, placement_type):
        """
        Check the result of a hero or monkey placement and warn if it failed.

        If the placement result is `False`, logs a warning that includes the target name,
        the attempted position, and the placement type.

        Parameters:
            result: The value returned by the placement call.
            target: The name of the hero or monkey being placed.
            pos: The position attempted for placement (e.g., (x, y) or a dict with x/y).
            placement_type: A label such as 'hero' or 'monkey' used in the warning message.
        """
        if result is False:
            logging.warning(
                f"{placement_type} placement returned False for {target} at {pos}."
            )

    def __init__(
        self, map_config: Dict[str, Any], global_config: Dict[str, Any]
    ) -> None:
        """
        Initialize the ActionManager with map and global configuration.

        Args:
            map_config (Dict[str, Any]): Map-specific configuration.
            global_config (Dict[str, Any]): Global configuration.
        """
        self.map_config = map_config
        self.global_config = global_config
        self.actions = sorted(
            map_config.get("actions", []), key=lambda a: a.get("step", 0)
        )
        self.pre_play_actions = sorted(
            map_config.get("pre_play_actions", []),
            key=lambda a: a.get("step", 0),
        )
        self.hero = map_config.get("hero", {})
        self.monkey_positions = self._build_monkey_position_lookup()
        self.completed_steps = set()
        self.timing = map_config.get("timing", {})

    def _normalize_position(self, pos: Any) -> Tuple[int, int]:
        """
        Normalize a position to an (x, y) tuple.
        Validates presence of 'x' and 'y' if pos is a dict, else expects a tuple/list of length 2.
        Raises ValueError on invalid formats.

        Args:
            pos (Any): Position as dict, tuple, or list.
        Returns:
            Tuple[int, int]: Normalized (x, y) position.
        Raises:
            ValueError: If position format is invalid.
        """
        if isinstance(pos, dict):
            if "x" in pos and "y" in pos:
                return (pos["x"], pos["y"])
            else:
                raise ValueError(f"Position dict missing 'x' or 'y': {pos}")
        elif isinstance(pos, (tuple, list)) and len(pos) == 2:
            return tuple(pos)
        else:
            raise ValueError(f"Invalid position format: {pos}")
        # ...existing code...
        for action in self.actions:
            if action.get("step") not in self.completed_steps:
                return action
        return None

    def mark_completed(self, step: int) -> None:
        """
        Mark an action step as completed.

        Args:
            step (int): The step number to mark as completed.
        """
        self.completed_steps.add(step)

    def steps_remaining(self) -> int:
        """
        Return the number of steps left in the routine.

        Returns:
            int: Number of remaining steps.
        """
        return len(
            [
                a
                for a in self.actions
                if a.get("step") not in self.completed_steps
            ]
        )

    def get_monkey_position(
        self, monkey_name: str
    ) -> Optional[Tuple[int, int]]:
        """
        Lookup the position of a monkey by name.

        Args:
            monkey_name (str): Name of the monkey.
        Returns:
            Optional[Tuple[int, int]]: (x, y) position or None if not found.
        """
        return self.monkey_positions.get(monkey_name)

    def run_pre_play(self) -> None:
        """
        Execute pre-play actions, including hero placement and monkey buys.
        Raises exceptions for invalid positions or placement errors.
        """
        # Place hero
        hero = self.hero
        if hero and "position" in hero:
            try:
                pos = self._normalize_position(hero["position"])
            except ValueError:
                logging.exception("Invalid hero position")
                raise
            hotkey = hero.get("hotkey")
            if not hotkey:
                # Defensive: require explicit hotkey or use dedicated hero_key from global config
                hero_key = self.global_config.get("hero_key", "u")
                if not hero_key:
                    logging.error(
                        "No hero hotkey defined in config and none provided in hero config."
                    )
                    raise ValueError(
                        "Hero hotkey must be defined in hero config or global config as 'hero_key'."
                    )
                hotkey = hero_key
            logging.info(f"Placing hero {hero.get('name', '')} at {pos}")
            try:
                result = place_hero(pos, hotkey)
                self._check_placement_result(
                    result, hero.get("name", ""), pos, "hero"
                )
            except Exception:
                logging.exception("Exception during hero placement")
                raise
            time.sleep(self.timing.get("placement_delay", 0.5))
        # Place pre-play monkeys
        for action in self.pre_play_actions:
            if action.get("action") == "buy":
                try:
                    pos = self._normalize_position(action["position"])
                except ValueError:
                    logging.exception(
                        f"Invalid position for monkey '{action['target']}'"
                    )
                    raise
                hotkey = action.get("hotkey")
                if not hotkey and "target" in action:
                    normalized_name = normalize_monkey_name_for_hotkey(
                        action["target"]
                    )
                    hotkey = get_monkey_hotkey(
                        normalized_name,
                        self.global_config.get("default_monkey_key", "q"),
                    )
                logging.info(f"Placing {action['target']} at {pos}")
                try:
                    result = place_monkey(pos, hotkey)
                    self._check_placement_result(
                        result, action["target"], pos, "monkey"
                    )
                except Exception:
                    logging.exception("Exception during monkey placement")
                    raise
                time.sleep(self.timing.get("placement_delay", 0.5))

    def run_buy_action(self, action: Dict[str, Any]) -> None:
        """
        Execute a buy action (place a monkey at a position).
        Raises exceptions for invalid positions or placement errors.

        Args:
            action (Dict[str, Any]): Action dictionary containing target and position.
        """
        try:
            pos = self._normalize_position(action["position"])
        except ValueError:
            logging.exception(
                f"Invalid position for monkey '{action['target']}'"
            )
            raise
        hotkey = action.get("hotkey")
        if not hotkey and "target" in action:
            normalized_name = normalize_monkey_name_for_hotkey(
                action["target"]
            )
            hotkey = get_monkey_hotkey(
                normalized_name,
                self.global_config.get("default_monkey_key", "q"),
            )
        logging.info(f"Placing {action['target']} at {pos}")
        try:
            result = place_monkey(pos, hotkey)
            self._check_placement_result(
                result, action["target"], pos, "monkey"
            )
        except Exception:
            logging.exception("Exception during monkey placement")
            raise
        time.sleep(self.timing.get("placement_delay", 0.5))

    def run_upgrade_action(self, action: Dict[str, Any]) -> None:
        """
        Execute an upgrade action for a tower.
        Clicks the tower at its position, checks cost, and presses the hotkey for the desired upgrade path.
        Only one upgrade is performed per action.

        Args:
            action (Dict[str, Any]): Action dictionary containing target and upgrade_path.
        """
        target = action.get("target")
        upgrade_path = action.get("upgrade_path", {})
        if not target or not upgrade_path:
            logging.warning("Upgrade action missing target or upgrade_path.")
            return

        # Get tower position
        pos = self.get_monkey_position(target)
        if not pos:
            logging.warning(
                f"No position found for tower '{target}' during upgrade."
            )
            return

        # Check if we can afford the upgrade
        # Use can_afford helper, which currently uses at_money for upgrades
        current_money = action.get("at_money", 0)
        if not can_afford(current_money, action, self.map_config):
            logging.info(
                f"Cannot afford upgrade for {target} at ${current_money}."
            )
            return

        # Click the tower to select it
        click(pos[0], pos[1], delay=0.2)

        # Determine which path to upgrade (only one per action)
        # upgrade_path is a dict like {"path_1": 0, "path_2": 0, "path_3": 1}
        # Find which path has changed (value incremented by 1)
        path_hotkeys = self.global_config.get("hotkey", {})
        path_map = {
            "path_1": "upgrade_path_1",
            "path_2": "upgrade_path_2",
            "path_3": "upgrade_path_3",
        }
        # Find which path index is being upgraded
        for path_key, hotkey_name in path_map.items():
            if upgrade_path.get(path_key, 0) > 0:
                # Press the hotkey for this path
                hotkey = path_hotkeys.get(hotkey_name)
                if not hotkey:
                    logging.warning(
                        f"No hotkey defined for {hotkey_name} in global config."
                    )
                    continue
                logging.info(
                    f"Upgrading {target} at {pos} via {hotkey_name} ({hotkey})"
                )
                keyboard.send(hotkey.lower())
                break  # Only one upgrade per action

        time.sleep(self.timing.get("upgrade_delay", 0.5))


# --- Stateless helpers ---
def _parse_tower_costs(
    tower_data: Dict[str, Any], difficulty: str, mode: str
) -> Optional[int]:
    """
    Determine a tower's in-game cost by parsing its cost string and applying difficulty/mode normalization.

    Parameters:
        tower_data (Dict[str, Any]): Tower entry from btd6_towers.json containing a "cost" string.
        difficulty (str): Difficulty label (e.g., "Easy", "Medium", "Hard"); will be normalized.
        mode (str): Game mode label (e.g., "Standard", "Impoppable"); will be normalized.

    Returns:
        Optional[int]: The resolved cost for the tower for the given difficulty and mode, or `None` if no applicable cost is found.

    Notes:
        - Parses numeric cost blocks from the tower's "cost" text and maps them to their labels.
        - If the normalized mode is "Impoppable" and normalized difficulty is "Hard", returns the "Impoppable" cost when present.
        - Otherwise returns the cost matching the normalized difficulty, falling back to the "Medium" cost if the specific label is missing.
    """
    cost_str = tower_data.get("cost", "")
    # Handle alternate cost strings (e.g., Sniper Monkey)
    # Only use the default cost block for now
    # Example: "Cost $170 ( Easy ) $200 ( Medium ) $215 ( Hard ) $240 ( Impoppable )"
    # For Impoppable, mode must be 'Impoppable' and difficulty 'Hard'

    costs = {}
    for match in _COST_REGEX.finditer(cost_str):
        value, label = match.groups()
        label = label.strip()
        costs[label] = int(value)
    norm_difficulty, norm_mode = _normalize_difficulty_mode(difficulty, mode)
    if norm_mode == "Impoppable" and norm_difficulty == "Hard":
        return costs.get("Impoppable")
    elif norm_difficulty in costs:
        return costs.get(norm_difficulty)
    return costs.get("Medium")


def can_afford(
    current_money: int,
    action: Dict[str, Any],
    map_config: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Determine whether available money covers the required cost for a buy or upgrade action.

    If map_config is provided, buy actions use tower pricing resolved from tower data for the configured difficulty and mode; upgrade actions use the action's `at_money` value. If map_config is omitted, the function falls back to the action's `at_money` value for cost. Missing tower data or unresolved costs cause the function to return `False` (and are logged).

    Parameters:
        current_money (int): Available money to compare against the required cost.
        action (Dict[str, Any]): Action dictionary; expected keys include `"action"` (e.g., `"buy"` or `"upgrade"`), `"target"` for buy actions, and `"at_money"` for fallback costs.
        map_config (Optional[Dict[str, Any]]): Optional map configuration containing `"difficulty"` and `"mode"` used to resolve tower costs.

    Returns:
        bool: `True` if `current_money` is greater than or equal to the action's required cost, `False` otherwise.
    """
    if map_config is None:
        # Fallback to hardcoded at_money if no config provided
        at_money = action.get("at_money", 0)
        return current_money >= at_money
    difficulty = map_config.get("difficulty", "Medium")
    mode = map_config.get("mode", "Standard")
    act_type = action.get("action", "").lower()
    if act_type == "buy":
        # Normalize tower name (strip trailing numbers)
        target = action.get("target", "")
        tower_name = _MONKEY_SUFFIX_REGEX.sub("", target).strip()
        tower_data = _get_tower_data(tower_name)
        if not tower_data:
            logging.warning(f"Tower data not found for {tower_name}")
            return False
        cost = _parse_tower_costs(tower_data, difficulty, mode)
        if cost is None:
            logging.warning(
                f"Cost not found for {tower_name} ({difficulty}, {mode})"
            )
            return False
        return current_money >= cost
    elif act_type == "upgrade":
        # TODO: Implement upgrade cost lookup
        return current_money >= action.get("at_money", 0)
    else:
        logging.warning(f"Unknown action type: {act_type}")
        return False
