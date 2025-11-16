# BTD6 Auto

BTD6 Auto is a Python automation bot for Bloons Tower Defense 6 (BTD6), designed to automate core gameplay actions such as placing towers, upgrading, and using abilities. The project aims to provide a modular, extensible, and reliable automation solution for BTD6, focusing exclusively on Windows environments.

## Project Goals

- **Automate core gameplay tasks**: Placing towers, upgrading, using abilities, and more.
- **Support for multiple heroes, towers, and maps**: Easily extendable to new game elements.
- **Modular and extensible codebase**: Designed for easy updates, testing, and community contributions.
- **Windows-only reliability**: All automation is tailored for Windows platforms.
- **Future enhancements**: Plans include GUI configuration, strategy profiles, and plugin support.

## Technical Overview

- **Language**: Python 3
- **Automation**: Uses `pyautogui` for mouse input simulation and `opencv-python` for image recognition. `BetterCam` for screencapture. `keyboard` for keyboard hotkeys. `pytesseract` for image2text (reading current money).
- **Configuration**: User preferences managed via configuration files.
- **Structure**: Organized for easy extension and maintenance.

## How to Run

1. **Windows Only**: This bot is intended for Windows. Linux/Mac are not supported.

2. **Install Requirements**:
   - Ensure uv is installed: `powershell -c "irm https://astral.sh/uv/install.ps1 | more"`
   - [Install Tesseract OCR 5.5.0](https://github.com/UB-Mannheim/tesseract/wiki) and make sure it's in PATH
   - Game must be ran in 1920x1080 fullscreen!

3. **Configure Preferences**:
   - Edit configuration files as needed for your setup.

4. **Launch the Bot**:
   - Use the provided Windows batch file, this will also install dependencies, including Python (3.12)

     ```cmd
     run_automation.cmd
     ```

## Notes

- The project is under active development. Features and instructions will evolve.
- Contributions and feedback are welcome!

## License

See `LICENSE` for details.
