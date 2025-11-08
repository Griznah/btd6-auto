"""
Action management and execution for BTD6 automation routines.

This module defines the ActionManager class, which tracks and manages the current action list for a map run, provides lookup for monkey positions, and orchestrates execution of pre-play and buy actions. Low-level stateless helpers are kept as standalone functions for testability and clarity.

Classes:
    ActionManager: Manages actions and monkey positions for a BTD6 map run.

Functions:
    can_afford: Dummy check for action affordability.
"""

from typing import Any, Dict, Optional, Tuple
import logging
import time
from btd6_auto.monkey_manager import place_monkey, place_hero
from btd6_auto.monkey_hotkey import get_monkey_hotkey

import re


def normalize_monkey_name_for_hotkey(monkey_name: str) -> str:
    """
    Strip trailing numeric suffixes (e.g., ' 01', ' 02') from monkey names for hotkey lookup.
    Args:
        monkey_name (str): The monkey name from config (e.g., 'Dart Monkey 01').
    Returns:
        str: Normalized monkey name (e.g., 'Dart Monkey').
    """
    return re.sub(r"\s\d+$", "", monkey_name)


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

    def _check_placement_result(self, result, target, pos, placement_type):
        """
        Unified checker for hero/monkey placement results.
        Logs a warning if result is False. Can be extended for stricter handling.

        Args:
            result: The return value from the placement function.
            target: The name of the hero/monkey.
            pos: The position attempted.
            placement_type: 'hero' or 'monkey' (for log clarity).
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

    def _build_monkey_position_lookup(self) -> Dict[str, Tuple[int, int]]:
        """
        Build a lookup table for monkey positions from pre-play and buy actions.

        Returns:
            Dict[str, Tuple[int, int]]: Mapping from monkey name to (x, y) position.
        """
        lookup = {}
        for action in self.pre_play_actions + self.actions:
            if (
                action.get("action") == "buy"
                and "target" in action
                and "position" in action
            ):
                try:
                    pos = self._normalize_position(action["position"])
                    lookup[action["target"]] = pos
                except ValueError as e:
                    logging.error(
                        f"Invalid position for monkey '{action['target']}': {e}"
                    )
        return lookup

    def get_next_action(self) -> Optional[Dict[str, Any]]:
        """
        Get the next pending action (lowest step not completed).

        Returns:
            Optional[Dict[str, Any]]: The next action dict, or None if all actions are completed.
        """
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
        Dummy function for upgrade actions. To be implemented.

        Args:
            action (Dict[str, Any]): Action dictionary containing target and upgrade path.
        """
        logging.info(
            f"[DUMMY] Would upgrade {action['target']} to {action.get('upgrade_path', '')}"
        )
        time.sleep(self.timing.get("upgrade_delay", 0.5))


# --- Stateless helpers ---
def can_afford(current_money: int, action: Dict[str, Any]) -> bool:
    """
    Dummy check if we can afford an action. Replace with real price logic.

    Args:
        current_money (int): Current available money.
        action (Dict[str, Any]): Action dictionary with 'at_money' key.
    Returns:
        bool: True if current_money >= at_money, else False.
    """
    at_money = action.get("at_money", 0)
    return current_money >= at_money


# Add more stateless helpers as needed.
