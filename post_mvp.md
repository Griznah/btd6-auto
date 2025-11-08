# BTD6 Bot: Production-Ready Refactor Plan

This document outlines a pragmatic, test-driven development plan to refactor the BTD6 Automation Bot into a robust, maintainable, and extensible platform.

🎯 Guiding Principles

* Configuration is Code: Our configs must be as reliable and predictable as our Python code. All strategies will be defined in validated, schema-driven JSON files.

* Idempotency and Retries: Automation actions must be safely repeatable. Failure is an expected condition and will be handled gracefully through configurable retry mechanisms.

* Test First, Test Always: No feature is complete until it's covered by an automated, offline test. This is non-negotiable for building a reliable automation system.

* Decouple Logic from Platform: The core strategy logic will have no knowledge of the underlying OS or whether it's interacting with the live game or a mocked test environment.

## Phase 1: The Foundation - Config, Core, and Testing (3-4 Weeks)

This phase is the most critical. We will build the new system's backbone and ensure it's built on a testable foundation from day one.

1. **Schema-Driven Configuration**:
   * Action: Implement the per-map and global JSON configuration system.
   * Technology: Utilize Pydantic to define configuration models. This provides automatic data validation, type hinting, and easy serialization/deserialization, preventing a wide class of configuration-related bugs.
   * Outcome: A ConfigManager class that can load, validate, and provide type-safe access to all settings for a given map strategy.

   **JSON Configuration Structure**

   **Map Configuration** (`configs/maps/{map_name}.json`)

   ```json
   {
   "map_name": "Monkey Meadow",
   "difficulty": "Easy",
   "mode": "Standard",
   "game_settings": {
      "window_title": "BloonsTD6",
      "resolution": "1920x1080",
      "fullscreen": true
   },
   "hero": {
      "name": "Quincy",
      "hotkey": "u",
      "position": {
         "x": 485,
         "y": 395
         },
         "abilities": [
         {
            "round": 1,
            "ability_type": "storm",
            "cooldown_rounds": 60
         }
         ]
      },
      "monkeys": [
      {
         "name": "Dart Monkey",
         "hotkey": "q",
         "position": {
         "x": 625,
         "y": 500
         },
         "upgrade_path": "0-0-2",
         "purchase_round": 1,
         "upgrades": [
         {
            "round": 3,
            "path": 0,
            "tier": 1
         },
         {
            "round": 6,
            "path": 0,
            "tier": 2
         },
         {
            "round": 10,
            "path": 2,
            "tier": 1
         }
         ]
      },
      {
         "name": "Bomb Shooter",
         "hotkey": "e",
         "position": {
         "x": 700,
         "y": 450
         },
         "upgrade_path": "2-0-3",
         "purchase_round": 4,
         "upgrades": [
         {
            "round": 7,
            "path": 2,
            "tier": 1
         },
         {
            "round": 12,
            "path": 0,
            "tier": 1
         }
         ]
      }
      ],
   "timing": {
      "map_load_delay": 7,
      "placement_delay": 0.5,
      "upgrade_delay": 1.0,
      "ability_delay": 0.3
   },
   "retries": {
      "max_retries": 3,
      "retry_delay": 1.0,
      "image_recognition_timeout": 5.0
   }
   }
   ```

   **Global Configuration** (`configs/global.json`)

   ```json
   {
   "automation": {
      "pause_between_actions": 0.1,
      "failsafe_enabled": true,
      "killswitch_key": "esc",
      "logging_level": "INFO"
   },
   "image_recognition": {
      "confidence_threshold": 0.8,
      "template_matching_method": "cv2.TM_CCOEFF_NORMED",
      "screenshot_delay": 0.2
   },
   "error_handling": {
      "max_consecutive_failures": 5,
      "recovery_delay": 2.0,
      "screenshot_on_error": true
   }
   }
   ```

2. **Refactor the Automation Core**
   * Action: Abstract all low-level automation actions (mouse clicks, key presses, screen grabs) into a dedicated AutomationProvider class.
   * Key Feature: Implement robust retry logic directly within this provider, likely using decorators. Every public method (click, find_image, etc.) will automatically use the retry settings defined in the global configuration.

   Example of a decorated, retry-able action

   ```python
   @retry(attempts_from_config, delay_from_config)
   def find_image_on_screen(self, image_template: str) -> Point:
       # ... OpenCV logic ...
   ```

   * Outcome: A clean, reliable, and testable interface for performing game actions, with error handling and retries built-in.

3. **Build the Offline Test Harness**
   * Action: Concurrently with the steps above, build the offline testing suite using pytest.
   * Strategy:
      * Create a _MockAutomationProvider_ that implements the same interface as the real provider but operates on static image files instead of the live game screen.
      * Write unit tests for the Pydantic configuration models and the _ConfigManager_.
      * Write integration tests that load a real map config (e.g., monkey_meadow.json) and run the strategy executor against the _MockAutomationProvider_ to verify the entire logic flow without ever launching the game.
   * Outcome: A CI/CD-friendly test suite that validates the core logic, ensuring that changes don't break existing functionality.

## **Phase 2: Execution and Expansion (2-3 Weeks)**

With a solid foundation, we can now reliably execute strategies and begin adding more content.

1. Develop the Strategy Executor

   Action: Build the main process loop that reads the purchase and upgrade order from a map's configuration and executes the actions using the AutomationProvider.

   Features:

   Waits for and validates game state transitions (e.g., waits for the "Next Round" button to appear before proceeding).

   Implements robust logging for every action, success, failure, and retry attempt.

   Captures a screenshot to a debug/ folder upon an unrecoverable failure, as suggested in the original roadmap.

   Outcome: A working bot that can reliably complete a full game on any correctly configured map.

2. Seed Content and Document

   Action: Migrate existing hardcoded strategies for Monkey Meadow and one or two other simple maps into the new JSON configuration format.

   Documentation: Create a clear CONFIG_GUIDE.md that explains every field in the JSON schema with concrete examples. This is crucial for enabling easy creation of new map strategies.

   Outcome: 2-3 fully working map configurations and the documentation needed for others to contribute more.

## Phase 3: Advanced Features and Hardening (4+ Weeks)

Now we can add the more complex features that make the bot truly intelligent and resilient.

1. Advanced Error Recovery

   Action: Move beyond simple retries. Implement state recovery logic for common interruptions.

   Example: If the bot detects it has been unexpectedly returned to the main menu, it should have a defined routine to navigate back to the correct map selection screen and attempt to resume the strategy.

   Outcome: A more resilient bot that can handle common game interruptions without requiring manual intervention.

2. Ability Usage and Dynamic Decisions

   * Action: Implement the "abilities" logic from the JSON configuration schema. This will require more advanced image recognition to check for ability cooldowns.

   * Future-Proofing: Design the system so that future conditional logic (e.g., "only use ability if more than 20 bloons are on screen") can be added without a major refactor.

   * Outcome: The bot can now strategically use hero and monkey abilities at specified rounds or intervals, enabling more complex strategies.

3. User Interface (Future Consideration)

   * Action: Once the core engine is stable and feature-complete, the next logical step is to build a simple GUI.

   * Goal: Allow users to create and edit map configurations visually, select which map to run, and monitor the bot's progress without directly editing JSON files.

   * Outcome: A significantly more user-friendly application accessible to a wider audience.
