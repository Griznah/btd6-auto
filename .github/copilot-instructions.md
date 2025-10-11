
# Workspace Instructions for Copilot

## Project Overview
This project is a Python3 automation bot for Bloons Tower Defense 6 (BTD6), a tower defense game. The bot automates gameplay actions and is designed exclusively for Windows platforms.

## Key Features & Goals
- Automate core gameplay tasks: placing towers, upgrading, using abilities.
- Support multiple heroes, towers, and maps.
- Modular, extensible codebase for easy updates and testing.
- Reliable automation for Windows environments only.

## Development Stages
1. Research & Planning: Identify Windows-specific automation methods, list supported game elements, define MVP.
2. Environment Setup: Use Python3, pyautogui for input, opencv for image recognition. Ensure compatibility with Windows.
3. Basic Automation: Implement screen capture and input simulation for Windows.
4. Advanced Features: Add hero selection, tower upgrades, map strategies, error handling, and logging.
5. Testing & Optimization: Offline testing on Linux, game testing on Windows, optimize, gather feedback.

## Technical Guidance
- DO NOT OVERENGINEER. Keep it simple and functional.
- Use OpenCV for image recognition and game state detection (preferred over Pillow for advanced vision tasks).
- Use pyautogui for mouse/keyboard automation.
- But use keyboard package for hero and monkey selection to avoid focus issues.
- Use pytest for unit testing.
- Organize code modularly for easy extension.
- Use configuration files for user preferences.

## File Naming Convention
Use `.yaml` for YAML files in this project. Do not use `.yml`.

## Future Ideas
- GUI for bot configuration.
