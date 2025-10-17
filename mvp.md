# MVP Plan for BTD6 Automation Bot

**Goal:**
Automate gameplay for Bloons Tower Defense 6 on one map, using one monkey and one hero, in Easy - Standard mode, exclusively on Windows.

## Features

1. Map Selection

    - Support only one predefined map (e.g., "Monkey Meadow").

2. Game Mode

    - Easy - Standard mode only.

3. Monkey Placement

    - Place a single type of monkey (e.g., Dart Monkey) at a fixed location.

4. Hero Placement

    - Place one hero (e.g., Quincy) at a fixed location.

5. Basic Automation

    - Start the game.
    - Place monkey and hero.

6. Screen Capture & Input Simulation

    - Use pyautogui for mouse/keyboard automation (Windows).
    - Use OpenCV for basic image recognition (e.g., detecting game state).

## Out of Scope (for MVP)

- Multiple maps, monkeys, or heroes.
- Advanced strategies or upgrades.
- GUI
