# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BTD6 Auto is a Python automation bot for Bloons Tower Defense 6 (BTD6) on Windows. The bot automates gameplay actions including tower placement, upgrades, and ability usage through computer vision and input simulation.

## Development Commands

### Environment Setup
```bash
# Install dependencies using uv
uv sync

# For ad-hoc package installation
uv pip install <package>
```

### Testing
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_vision.py

# Run tests with verbose output
pytest -v tests/
```

### Running the Application
```bash
# Main entry point (Windows batch file handles Python installation)
run_automation.cmd
```

## Core Architecture

### Main Components

- **actions.py**: Core ActionManager class that orchestrates gameplay actions, manages monkey positions, and handles pre-play routines
- **vision.py**: Screen capture (BetterCam) and image recognition (OpenCV) with OCR functionality for reading game state
- **monkey_manager.py**: Tower and hero selection/placement logic with targeting verification
- **input.py**: Mouse and keyboard input simulation using pyautogui and keyboard packages
- **state.py**: Shared state management across modules (kill switches, flags)
- **config_loader.py**: Configuration management system with JSON-based configs
- **currency_reader.py**: OCR-based currency reading from game UI
- **game_launcher.py**: BTD6 window activation and management
- **overlay.py**: UI overlay for bot status and debugging

### Configuration System

- Global config: `btd6_auto/configs/global.json`
- Map-specific configs: `btd6_auto/configs/maps/{map_name}.json`
- Tower data: `data/btd6_towers.json`
- Game facts: `data/btd6_facts.json`

### Key Dependencies

- **pyautogui**: Mouse input simulation
- **opencv-python**: Image recognition and processing
- **bettercam**: High-performance screen capture
- **pytesseract**: OCR for reading currency and game text
- **keyboard**: Keyboard input (preferred over pyautogui for hero/monkey selection)
- **numpy**: Numerical operations for image processing

## Development Guidelines

### Code Style
- Follow PEP8 Python style guide
- Use markdownlint for markdown files
- Keep imports at the top of each file
- Use type hints where appropriate

### Platform Considerations
- Windows-only application
- Use backslashes for paths or `os.path.join()` for compatibility
- Game must run in 1920x1080 fullscreen mode
- Requires Tesseract OCR 5.5.0+ in PATH

### Testing and Quality
- All new features should include unit tests
- Use pytest for testing framework
- Test files should be named `test_*.py` and placed in `tests/` directory
- Maintain test coverage for critical functionality

### Vision and Input Patterns
- Use OpenCV over Pillow for advanced vision tasks
- Use keyboard package for hero/monkey selection to avoid focus issues
- Implement retry logic with proper error handling for vision-based operations
- Use verify_image_difference() for confirming UI changes after actions

### Configuration Management
- Use ConfigLoader for accessing configuration values
- Map configurations should contain tower positions and strategies
- Global config contains cross-map settings and preferences

## Important Notes

- This is a game automation bot - ensure all testing respects game terms of service
- The bot uses computer vision to detect game state and make decisions
- All coordinates and regions are based on 1920x1080 resolution
- Error handling should be robust to handle game state changes and UI variations