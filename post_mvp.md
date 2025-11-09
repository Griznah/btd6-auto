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
      "pre_play_actions": [
         {
            "step": 0,
            "action": "buy",
            "target": "Dart Monkey 01",
            "position": { "x": 490, "y": 500 }
         },
         {
            "step": 1,
            "action": "buy",
            "target": "Dart Monkey 02",
            "position": { "x": 650, "y": 520 }
         }
      ],
      "hero": {
         "name": "Any",
         "hotkey": "u",
         "position": { "x": 485, "y": 395 }
      },
      "actions": [
         {
            "step": 1,
            "at_money": 75,
            "action": "upgrade",
            "target": "Dart Monkey 01",
            "upgrade_path": { "path_1": 0, "path_2": 0, "path_3": 1 }
         },
         {
            "step": 2,
            "at_money": 210,
            "action": "buy",
            "target": "Wizard Monkey 01",
            "position": { "x": 400, "y": 395 }
         },
         {
            "step": 3,
            "at_money": 170,
            "action": "upgrade",
            "target": "Dart Monkey 01",
            "upgrade_path": { "path_1": 0, "path_2": 0, "path_3": 2 }
         },
         {
            "step": 4,
            "at_money": 700,
            "action": "buy",
            "target": "Spike Factory 01",
            "position": { "x": 680, "y": 765 }
         },
         {
            "step": 5,
            "at_money": 500,
            "action": "upgrade",
            "target": "Dart Monkey 02",
            "upgrade_path": { "path_1": 0, "path_2": 1, "path_3": 0 }
         }
      ]
   }
   ```

2. **Refactor the Automation Core**
   * Action: Abstract all low-level automation actions (mouse clicks, key presses, screen grabs) into a dedicated AutomationProvider class.
   * Key Feature: Implement robust retry logic directly within this provider, likely using decorators. Every public method (click, find_image, etc.) will automatically use the retry settings defined in the global configuration.

   Example of a decorated, retry-able action

    @retry(attempts_from_config, delay_from_config)
    def find_image_on_screen(self, image_template: str) -> Point:
        # ... OpenCV logic ...

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
