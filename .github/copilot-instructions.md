# Workspace Instructions for Copilot

## Project Overview

This project is a Python3 automation bot for Bloons Tower Defense 6 (BTD6), a tower defense game. The bot automates gameplay actions and is designed exclusively for Windows platforms.

## Key Features & Goals

- Automate core gameplay tasks: placing towers, upgrading, using abilities.
- Support multiple heroes, towers, and maps.
- Modular, extensible codebase for easy updates and testing.
- Reliable automation for Windows environments only.

## Technical Guidance

- Follow PEP8 Style Guide for Python
- Follow markdownlint style guide for markdown
- DO NOT OVERENGINEER. Keep it simple and functional.
- Use OpenCV for image recognition and game state detection (preferred over Pillow for advanced vision tasks).
- Use pyautogui for mouse/keyboard automation.
- But use keyboard package for hero and monkey selection to avoid focus issues.
- Use pytest for unit testing. All new features should include corresponding unit tests.
- Organize code modularly for easy extension.
- Use configuration files for user preferences.

## Configuration Files and facts

- Global config is stored in ./btd6_auto/configs/global.json
- Map specific config is stored in btd6_auto/configs/maps/{map_name}.json
- We have all tower facts stored in ./data/btd6_towers.json

## File Naming Convention

- Use `.yaml` for YAML files in this project. Do not use `.yml`.
- This project is developed and run exclusively on Windows. All file and directory names, as well as path handling, must be compatible with Windows conventions:

## Windows Platform Note

- Use backslashes (`\`) for paths in code, or use `os.path.join` for cross-version compatibility. Example:

```python
import os
config_path = os.path.join("btd6_auto", "configs", "global.json")
```
- Avoid reserved Windows filenames (e.g., `CON`, `PRN`, `AUX`, `NUL`, etc.).
- Be aware that Windows file systems are case-insensitive by default.
- Spaces in filenames are allowed, but consider using underscores or CamelCase for consistency.
- Always test file and directory creation on Windows to ensure compatibility.

## Contributing

- Fork the repository and create feature branches.
- Submit pull requests with clear descriptions.
- Follow branch naming conventions: `feature/`, `bugfix/`, etc.

## Running Tests

- Run all tests with: `pytest tests/`
- Ensure new code is covered by tests.

## Adding Dependencies

- Add new packages under `[project.dependencies]` in `pyproject.toml`.
- After updating dependencies, run tests to ensure compatibility.
- Install with: `uv sync` (or `uv pip install <package>` for ad-hoc testing).



This note should be reviewed by all contributors.