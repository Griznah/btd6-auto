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
- **Automation**: Uses `pyautogui` for input simulation and `opencv` for image recognition. `dxcam` for screencapture.
- **Configuration**: User preferences managed via configuration files.
- **Structure**: Organized for easy extension and maintenance.

## How to Run

1. **Windows Only**: This bot is intended for Windows. Linux/Mac are not supported for automation.

2. **Install Requirements**:
   - Ensure Python 3 is installed.
   - Install dependencies:

     ```bash
     pip install -r requirements.txt
     ```

3. **Configure Preferences**:
   - Edit configuration files as needed for your setup.

4. **Launch the Bot**:
   - Run the main script:

     ```bash
     python main.py
     ```

   - Or use the provided Windows batch file:

     ```cmd
     run_automation.cmd
     ```

## Notes

- The project is under active development. Features and instructions will evolve.
- Contributions and feedback are welcome!

## License

See `LICENSE` for details.
