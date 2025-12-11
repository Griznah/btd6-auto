"""
BTD6 Automation Action Management

This module provides core routines for managing and executing gameplay actions in Bloons Tower Defense 6 automation.
It defines the ActionManager class, which orchestrates map-specific and global actions, including tower placement, upgrades, and hero management.
Stateless helper functions are included for cost calculation, action affordability checks, and normalization utilities.

Key Components:
    - ActionManager: Tracks and executes actions for a BTD6 map run, manages monkey positions, and handles pre-play routines.
    - can_afford: Determines if a buy or upgrade action can be afforded based on current currency and game configuration.
    - Helper functions: Parse tower costs, normalize names, and retrieve tower data from JSON resources.

This module is designed for extensibility and testability, following project conventions and PEP 257 docstring standards.
"""

from typing import Any, Dict, Optional, Tuple
import json
import re
from functools import lru_cache
from pathlib import Path
import logging
import time
import keyboard

from .monkey_manager import (
    place_monkey,
    place_hero,
    try_targeting_success,
    get_regions_for_monkey,
)
from .vision import verify_image_difference, handle_vision_error, capture_region
from .monkey_hotkey import get_monkey_hotkey
from .config_loader import get_tower_positions_for_map
from .input import move_and_click, cursor_resting_spot
from .game_launcher import activate_btd6_window
from .currency_reader import CurrencyReader
from .debug_manager import DebugManager


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
    Normalize a monkey name for hotkey lookup by removing trailing numeric suffixes.
    Used to map config monkey names to their hotkey mapping.
    Args:
        monkey_name (str): Monkey name from config (e.g., "Dart Monkey 01").
    Returns:
        str: Normalized monkey name (e.g., "Dart Monkey").
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
    timing (Dict[str, Any]): Timing configuration for delays, loaded from global_config['automation']['timing'].
    """

    def get_next_action(self) -> Optional[Dict[str, Any]]:
        """
        Get the next uncompleted action from the main action list.
        Returns:
            Optional[Dict[str, Any]]: The next action dict, or None if all are completed.
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
            raise ValueError("Map name not found in config; position lookup will be empty")
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
        self,
        map_config: Dict[str, Any],
        global_config: Dict[str, Any],
        currency_reader: Optional[CurrencyReader] = None,
        debug_manager: Optional[DebugManager] = None,
    ) -> None:
        """
        Initialize the ActionManager with map and global configuration.

        Args:
            map_config (Dict[str, Any]): Map-specific configuration.
            global_config (Dict[str, Any]): Global configuration.
            currency_reader (Optional[CurrencyReader]): CurrencyReader instance for reading in-game currency.
            debug_manager (Optional[DebugManager]): DebugManager instance for logging and performance tracking.
        """
        self.map_config = map_config
        self.global_config = global_config
        self.actions = sorted(map_config.get("actions", []), key=lambda a: a.get("step", 0))
        self.pre_play_actions = sorted(
            map_config.get("pre_play_actions", []),
            key=lambda a: a.get("step", 0),
        )
        self.hero = map_config.get("hero", {})
        self.monkey_positions = self._build_monkey_position_lookup()
        self.completed_steps = set()
        self.timing = global_config.get("automation", {}).get("timing", {})
        self.monkey_upgrade_state = {}
        self.currency_reader = currency_reader
        self.debug_manager = debug_manager or DebugManager(global_config.get("debug", {}))

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
        Mark a given action step as completed.
        Args:
            step (int): The step number to mark as completed.
        """
        self.completed_steps.add(step)

    def steps_remaining(self) -> int:
        """
        Count the number of remaining (uncompleted) steps in the main action list.
        Returns:
            int: Number of remaining steps.
        """
        return len([a for a in self.actions if a.get("step") not in self.completed_steps])

    def get_monkey_position(self, monkey_name: str) -> Optional[Tuple[int, int]]:
        """
        Get the (x, y) position of a monkey by name from the position lookup.
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
        operation_id = self.debug_manager.start_performance_tracking("pre_play")
        self.debug_manager.log_detailed("ActionManager", "Starting pre-play routine",
                                      hero_count=1 if self.hero else 0,
                                      pre_play_actions=len(self.pre_play_actions))

        # Place hero
        hero = self.hero
        if hero and "position" in hero:
            hero_op_id = self.debug_manager.start_performance_tracking("place_hero")
            self.debug_manager.log_detailed("ActionManager", "Placing hero",
                                          hero_name=hero.get('name', ''),
                                          position=hero.get("position"))

            try:
                pos = self._normalize_position(hero["position"])
                self.debug_manager.log_verbose("ActionManager", "Normalized hero position",
                                             data={"normalized_pos": pos})
            except ValueError as e:
                self.debug_manager.log_error("ActionManager", e,
                                           context={"hero": hero, "position": hero.get("position")})
                logging.exception("Invalid hero position")
                raise
            hotkey = hero.get("hotkey")
            if not hotkey:
                # Defensive: require explicit hotkey or use dedicated hero_key from global config
                hero_key = self.global_config.get("hero_key", "u")
                if not hero_key:
                    error_msg = "No hero hotkey defined in config and none provided in hero config."
                    self.debug_manager.log_basic("ActionManager", error_msg, "error")
                    logging.error(error_msg)
                    raise ValueError(
                        "Hero hotkey must be defined in hero config or global config as 'hero_key'."
                    )
                hotkey = hero_key

            logging.info(f"Placing hero {hero.get('name', '')} at {pos}")
            try:
                result = place_hero(pos, hotkey)
                self._check_placement_result(result, hero.get("name", ""), pos, "hero")
                self.debug_manager.log_action("place_hero", hero.get("name", ""), result)
            except Exception as e:
                self.debug_manager.log_error("ActionManager", e,
                                           context={"hero": hero, "position": pos, "hotkey": hotkey})
                logging.exception("Exception during hero placement")
                raise

            self.debug_manager.finish_performance_tracking(hero_op_id)
            time.sleep(self.timing.get("placement_delay", 0.5))

        # Place pre-play monkeys
        for idx, action in enumerate(self.pre_play_actions):
            if action.get("action") == "buy":
                monkey_op_id = self.debug_manager.start_performance_tracking("place_monkey")
                self.debug_manager.log_detailed("ActionManager", f"Placing pre-play monkey {idx+1}",
                                              target=action.get('target'),
                                              step=action.get('step'))

                try:
                    pos = self._normalize_position(action["position"])
                    self.debug_manager.log_verbose("ActionManager", "Normalized monkey position",
                                                 data={"action": action, "normalized_pos": pos})
                except ValueError as e:
                    self.debug_manager.log_error("ActionManager", e,
                                               context={"action": action, "position": action.get("position")})
                    logging.exception(f"Invalid position for monkey '{action['target']}'")
                    raise
                hotkey = action.get("hotkey")
                if not hotkey and "target" in action:
                    normalized_name = normalize_monkey_name_for_hotkey(action["target"])
                    hotkey = get_monkey_hotkey(
                        normalized_name,
                        self.global_config.get("default_monkey_key", "q"),
                    )
                logging.info(f"Placing {action['target']} at {pos}")
                try:
                    result = place_monkey(pos, hotkey)
                    self._check_placement_result(result, action["target"], pos, "monkey")
                    self.debug_manager.log_action("place_monkey", action["target"], result,
                                                details={"hotkey": hotkey, "position": pos})
                except Exception as e:
                    self.debug_manager.log_error("ActionManager", e,
                                               context={"action": action, "position": pos, "hotkey": hotkey})
                    logging.exception("Exception during monkey placement")
                    raise

                self.debug_manager.finish_performance_tracking(monkey_op_id)
                time.sleep(self.timing.get("placement_delay", 0.5))

        self.debug_manager.finish_performance_tracking(operation_id)
        self.debug_manager.log_basic("ActionManager", "Pre-play routine completed")

    def run_buy_action(self, action: Dict[str, Any]) -> None:
        """
        Execute a buy action (place a monkey at a position).
        Raises exceptions for invalid positions or placement errors.

        Args:
            action (Dict[str, Any]): Action dictionary containing target and position.
        """
        operation_id = self.debug_manager.start_performance_tracking("buy_action")
        self.debug_manager.log_detailed("ActionManager", "Starting buy action",
                                      target=action.get('target'),
                                      step=action.get('step'))

        activate_btd6_window()
        try:
            pos = self._normalize_position(action["position"])
            self.debug_manager.log_verbose("ActionManager", "Normalized position",
                                         data={"action": action, "normalized_pos": pos})
        except ValueError as e:
            self.debug_manager.log_error("ActionManager", e,
                                       context={"action": action, "position": action.get("position")})
            logging.exception(f"Invalid position for monkey '{action['target']}'")
            raise
        hotkey = action.get("hotkey")
        if not hotkey and "target" in action:
            normalized_name = normalize_monkey_name_for_hotkey(action["target"])
            hotkey = get_monkey_hotkey(
                normalized_name,
                self.global_config.get("default_monkey_key", "q"),
            )
            self.debug_manager.log_detailed("ActionManager", "Resolved hotkey from target name",
                                          target=action["target"],
                                          normalized_name=normalized_name,
                                          hotkey=hotkey)

        logging.info(f"Placing {action['target']} at {pos}")
        try:
            result = place_monkey(pos, hotkey)
            self._check_placement_result(result, action["target"], pos, "monkey")
            self.debug_manager.log_action("place_monkey", action["target"], result,
                                        details={"hotkey": hotkey, "position": pos, "step": action.get("step")})
        except Exception as e:
            self.debug_manager.log_error("ActionManager", e,
                                       context={"action": action, "position": pos, "hotkey": hotkey})
            logging.exception("Exception during monkey placement")
            raise

        self.debug_manager.finish_performance_tracking(operation_id)
        time.sleep(self.timing.get("placement_delay", 0.5))

    def run_upgrade_action(self, action: Dict[str, Any]) -> None:
        """
        Execute a single upgrade for a monkey/tower, upgrading only one path per call, with vision-based verification and retry logic.
        The action's 'upgrade_path' dict must contain exactly one path (e.g., {"path_2": 1}).

        Args:
            action (Dict[str, Any]): Action dict with 'target' and single-key 'upgrade_path'.
        """
        operation_id = self.debug_manager.start_performance_tracking("upgrade_action")
        self.debug_manager.log_detailed("ActionManager", "Starting upgrade action",
                                      target=action.get('target'),
                                      upgrade_path=action.get('upgrade_path'),
                                      step=action.get('step'))

        activate_btd6_window()

        # Check if CurrencyReader is available
        if not self.currency_reader:
            error_msg = "No CurrencyReader provided to ActionManager. Skipping upgrade action."
            self.debug_manager.log_basic("ActionManager", error_msg, "warning")
            logging.warning(error_msg)
            return

        target = action.get("target")
        upgrade_path = action.get("upgrade_path", {})
        if not target or not upgrade_path:
            error_msg = "Upgrade action missing target or upgrade_path."
            self.debug_manager.log_basic("ActionManager", error_msg, "warning")
            logging.warning(error_msg)
            return

        if len(upgrade_path) != 1:
            error_msg = f"Upgrade action for '{target}' must specify exactly one path in upgrade_path, got: {upgrade_path}"
            self.debug_manager.log_basic("ActionManager", error_msg, "warning")
            logging.warning(error_msg)
            return

        path_key, requested = next(iter(upgrade_path.items()))
        if path_key not in ("path_1", "path_2", "path_3"):
            error_msg = f"Invalid path key '{path_key}' in upgrade_path for '{target}'."
            self.debug_manager.log_basic("ActionManager", error_msg, "warning")
            logging.warning(error_msg)
            return

        pos = self.get_monkey_position(target)
        if not pos:
            error_msg = f"No position found for tower '{target}' during upgrade."
            self.debug_manager.log_basic("ActionManager", error_msg, "warning")
            logging.warning(error_msg)
            return

        current_tiers = self.monkey_upgrade_state.get(
            target, {"path_1": 0, "path_2": 0, "path_3": 0}
        )
        current = current_tiers.get(path_key, 0)

        self.debug_manager.log_verbose("ActionManager", "Current upgrade state",
                                     data={
                                         "target": target,
                                         "current_tiers": current_tiers,
                                         "path_key": path_key,
                                         "current_tier": current,
                                         "requested_tier": requested
                                     })

        # Check if already at or beyond requested tier
        if current >= requested:
            info_msg = f"No upgrade needed for {target} {path_key}: current tier {current}, requested {requested}."
            self.debug_manager.log_basic("ActionManager", info_msg, "info")
            logging.info(info_msg)
            self.mark_completed(action.get("step", -1))
            return

        # Calculate the next tier (always upgrade by exactly 1)
        next_tier = current + 1

        # Check max tier boundary (BTD6 max is 5)
        if next_tier > 5:
            warning_msg = f"Cannot upgrade {target} {path_key} beyond tier 5. Current: {current}, Requested: {requested}"
            self.debug_manager.log_basic("ActionManager", warning_msg, "warning")
            logging.warning(warning_msg)
            self.mark_completed(action.get("step", -1))
            return

        path_hotkeys = self.global_config.get("hotkey", {})
        path_map = {
            "path_1": "upgrade_path_1",
            "path_2": "upgrade_path_2",
            "path_3": "upgrade_path_3",
        }
        hotkey_name = path_map[path_key]
        hotkey = path_hotkeys.get(hotkey_name)
        if not hotkey:
            error_msg = f"No hotkey defined for {hotkey_name} in global config."
            self.debug_manager.log_basic("ActionManager", error_msg, "warning")
            logging.warning(error_msg)
            return

        # Use vision-based targeting to select the monkey before upgrade
        targeting_op_id = self.debug_manager.start_performance_tracking("upgrade_targeting")
        self.debug_manager.log_detailed("ActionManager", "Starting targeting for upgrade",
                                      target=target, position=pos)

        regions = get_regions_for_monkey()
        max_attempts = regions["max_attempts"]
        targeting_threshold = regions["place_threshold"]
        targeting_region_1 = regions["target_region_1"]
        targeting_region_2 = regions["target_region_2"]

        targeting_success, region_id, targeted_img = try_targeting_success(
            pos,
            targeting_region_1,
            targeting_region_2,
            targeting_threshold,
            max_attempts,
            0.2,
            verify_image_difference,
        )

        self.debug_manager.log_vision_result("targeting_for_upgrade", targeting_success,
                                            confidence=targeting_threshold,
                                            match_info={"region_id": region_id, "target": target})

        if not targeting_success or targeted_img is None:
            error_msg = f"Upgrade targeting failed for {target} at {pos}"
            self.debug_manager.log_error("ActionManager", Exception(error_msg),
                                       context={"target": target, "position": pos, "region_id": region_id})
            logging.error(error_msg)
            handle_vision_error()
            return

        # Determine which region to use for verification
        verification_region = (
            targeting_region_1 if region_id == "region1" else targeting_region_2
        )

        self.debug_manager.finish_performance_tracking(targeting_op_id)

        # Read retry config from global config
        retries_cfg = self.global_config.get("automation", {}).get("retries", {})
        max_retries = retries_cfg.get("max_retries", 3)
        retry_delay = retries_cfg.get("retry_delay", 0.5)

        self.debug_manager.log_detailed("ActionManager", "Starting upgrade attempts",
                                      target=target, path_key=path_key, next_tier=next_tier,
                                      max_retries=max_retries)

        # Perform single upgrade with retries
        verified = False
        for attempt in range(1, max_retries + 1):
            self.debug_manager.add_checkpoint(operation_id, f"upgrade_attempt_{attempt}")

            info_msg = f"[Upgrade] Attempt {attempt}/{max_retries}: {target} {path_key} to tier {next_tier} via {hotkey_name} ({hotkey})"
            self.debug_manager.log_detailed("ActionManager", info_msg,
                                          attempt=attempt, target=target, path_key=path_key,
                                          next_tier=next_tier, hotkey=hotkey)
            logging.info(info_msg)

            keyboard.send(hotkey.lower())
            time.sleep(self.timing.get("upgrade_delay", 0.3))

            # Vision-based verification
            verification_op_id = self.debug_manager.start_performance_tracking("upgrade_verification")
            post_img = capture_region(verification_region)
            success, diff = verify_image_difference(targeted_img, post_img, threshold=15.0)

            verification_time = self.debug_manager.finish_performance_tracking(verification_op_id)

            self.debug_manager.log_vision_result("upgrade_verification", success,
                                                confidence=diff,
                                                match_info={
                                                    "target": target,
                                                    "path_key": path_key,
                                                    "next_tier": next_tier,
                                                    "attempt": attempt,
                                                    "threshold": 15.0
                                                },
                                                processing_time=verification_time)

            info_msg = f"Upgrade verification for {target} {path_key} tier {next_tier}: success={success}, diff={diff:.2f}"
            self.debug_manager.log_detailed("ActionManager", info_msg,
                                          success=success, diff=diff, attempt=attempt)
            logging.info(info_msg)

            if success:
                # Update upgrade state after verified success
                current_tiers[path_key] = next_tier
                verified = True
                self.debug_manager.log_action("upgrade", target, True,
                                            details={"path_key": path_key, "tier": next_tier,
                                                   "attempts": attempt, "diff": diff})
                break
            else:
                time.sleep(retry_delay)

        if not verified:
            error_msg = f"Upgrade verification failed for {target} {path_key} to tier {next_tier} after {max_retries} attempts."
            self.debug_manager.log_error("ActionManager", Exception(error_msg),
                                       context={"target": target, "path_key": path_key,
                                              "next_tier": next_tier, "max_retries": max_retries})
            logging.error(error_msg)
            # Do not raise, just continue to next action

        # Always move cursor away after upgrade attempt
        coords = cursor_resting_spot()
        move_and_click(coords[0], coords[1])
        time.sleep(self.timing.get("upgrade_delay", 0.5))

        # Save updated state
        self.monkey_upgrade_state[target] = current_tiers

        self.debug_manager.log_verbose("ActionManager", "Updated upgrade state",
                                     data={"target": target, "new_tiers": current_tiers})

        # Only mark as completed if we've reached the requested tier
        if verified and next_tier >= requested:
            self.debug_manager.log_basic("ActionManager", f"Upgrade completed: {target} {path_key} tier {next_tier}")
            self.mark_completed(action.get("step", -1))
        elif not verified:
            error_msg = f"Failed to upgrade {target} {path_key} to tier {next_tier} after {max_retries} attempts"
            self.debug_manager.log_error("ActionManager", Exception(error_msg),
                                       context={"target": target, "path_key": path_key,
                                              "next_tier": next_tier, "max_retries": max_retries})
            logging.error(error_msg)

        self.debug_manager.finish_performance_tracking(operation_id)


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


def _get_upgrade_cost(
    tower_data: Dict[str, Any],
    path_index: int,
    tier: int,
    difficulty: str,
    mode: str,
) -> Optional[int]:
    """
    Extract the upgrade cost for a given tower, path, and tier.
    Args:
        tower_data (dict): Tower entry from btd6_towers.json.
        path_index (int): Path number (1, 2, or 3).
        tier (int): Upgrade tier (0-4).
        difficulty (str): Difficulty label.
        mode (str): Mode label.
    Returns:
        Optional[int]: The cost for the upgrade, or None if not found.
    """
    path_key = f"Path {path_index}"
    upgrade_paths = tower_data.get("upgrade_paths", {})
    upgrades = upgrade_paths.get(path_key)
    if not upgrades or tier < 0 or tier >= len(upgrades):
        return None
    costs = upgrades[tier].get("costs", [])
    # costs: [Easy, Medium, Hard, Impoppable]
    norm_difficulty, norm_mode = _normalize_difficulty_mode(difficulty, mode)
    # Map difficulty/mode to index
    cost_idx = {"Easy": 0, "Medium": 1, "Hard": 2, "Impoppable": 3}
    if norm_mode == "Impoppable" and norm_difficulty == "Hard":
        idx = cost_idx["Impoppable"]
    else:
        idx = cost_idx.get(norm_difficulty, 1)
    if idx >= len(costs):
        return None
    return costs[idx]


def can_afford(
    current_money: int,
    action: Dict[str, Any],
    map_config: [Dict[str, Any]],
) -> bool:
    """
    Determine whether available money covers the required cost for a buy or upgrade action.

    For buy actions, uses tower pricing from tower data for the configured difficulty and mode.
    For upgrade actions, looks up the upgrade cost from tower data using path/tier/difficulty/mode.
    Missing tower data or unresolved costs cause the function to return `False` (and are logged).

    Parameters:
        current_money (int): Available money to compare against the required cost.
        action (Dict[str, Any]): Action dictionary; expected keys include "action", "target", "upgrade_path".
        map_config ([Dict[str, Any]]): Required map configuration containing "difficulty" and "mode".

    Returns:
        bool: `True` if `current_money` is greater than or equal to the action's required cost, `False` otherwise.
    """
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
            logging.warning(f"Cost not found for {tower_name} ({difficulty}, {mode})")
            return False
        return current_money >= cost
    elif act_type == "upgrade":
        target = action.get("target", "")
        tower_name = _MONKEY_SUFFIX_REGEX.sub("", target).strip()
        tower_data = _get_tower_data(tower_name)
        if not tower_data:
            logging.warning(f"Tower data not found for {tower_name}")
            return False
        upgrade_path = action.get("upgrade_path", {})
        # Find which path is being upgraded (value > 0)
        path_idx = None
        tier = None
        for i in range(1, 4):
            key = f"path_{i}"
            val = upgrade_path.get(key, 0)
            if val > 0:
                path_idx = i
                tier = val - 1  # val is the new tier (1-based), index is 0-based
                break
        if path_idx is None or tier is None:
            logging.warning(f"Upgrade action missing valid path/tier: {upgrade_path}")
            return False
        cost = _get_upgrade_cost(tower_data, path_idx, tier, difficulty, mode)
        if cost is None:
            logging.warning(
                f"Upgrade cost not found for {tower_name} path {path_idx} tier {tier} ({difficulty}, {mode})"
            )
            return False
        return current_money >= cost
    else:
        logging.warning(f"Unknown action type: {act_type}")
        return False
