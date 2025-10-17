# BTD6 Automation Bot: Next Phases of Development

## 1. Refactor: Per-Map Configuration System

- **Goal:** Move from a monolithic config to individual JSON config files for each map.
- **Contents of Each Config:**
  - Map name and metadata.
  - Hero selection and placement coordinates.
  - Monkey selection, placement coordinates, and upgrade paths.
  - Order of monkey purchases and upgrades.
  - Retry settings for selections, placements, and image recognition.
- **Benefits:** Easier to add new maps, customize strategies, and maintain configs.

## 2. Robust Retry Mechanisms

- **Implement Retries For:**
  - Hero and monkey selection (keyboard and mouse).
  - Image recognition (OpenCV).
  - Monkey placement and upgrades.
- **Configurable:** Number of retries and delay between attempts settable in config.

## 3. Offline Testing Suite

- **Cross-Platform:** Ensure tests run on both Linux and Windows.
- **Test Types:**
  - Unit tests for config parsing and logic.
  - Mocked input/output for automation routines.
  - Image recognition tests using sample screenshots.
- **Tools:** Use `pytest` for Python unit tests.

## 4. Additional Improvements

- **Extensible Configs:** Allow easy addition of new heroes, monkeys, and strategies.
- **Error Handling & Logging:** Improve logging for failed actions and retries.
- **Documentation:** Update README and add docs for config format and usage.
- **User Preferences:** Store user settings in a separate config file.
- **Future-Proofing:** Design configs to support future features (e.g., ability usage, advanced strategies).

## 5. Roadmap

1. Design JSON schema for per-map configs.
2. Refactor codebase to load and use map-specific configs.
3. Implement retry logic and make it configurable.
4. Expand and improve offline test coverage.
5. Update documentation and provide config examples.
6. Gather feedback and iterate.
