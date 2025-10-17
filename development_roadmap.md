# BTD6 Auto - Next Phase Development Roadmap

## Overview

This document outlines the next phases of development for the BTD6 Automation Bot, moving beyond the current MVP to create a more robust, extensible, and user-friendly automation system.

## Phase 1: Map-Specific Configuration System

### Current State

- Configuration is hardcoded in `config.py` with fixed values for one map (Monkey Meadow)
- Single monkey type (Dart Monkey) and hero (Quincy) hardcoded
- Fixed coordinates and key bindings

### Goals

- **Individual JSON configuration files per map**
- **Support a hero and multiple monkeys per map**
- **Configurable upgrade paths and purchase order**
- **Dynamic coordinate and key binding system**

### JSON Configuration Structure

#### Map Configuration (`configs/maps/{map_name}.json`)

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
    "key_binding": "u",
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
      "key_binding": "q",
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
      "key_binding": "e",
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

#### Global Configuration (`configs/global.json`)

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

## Phase 2: Enhanced Error Handling & Retry System

### Features

- **Configurable retry limits** for all operations (selections, image recognition, placements)
- **Exponential backoff** for repeated failures
- **Screenshot capture** on errors for debugging
- **Graceful degradation** when operations fail
- **Recovery mechanisms** for common failure scenarios

### Implementation

- Wrapper functions around all automation calls with retry logic
- Context managers for operation timing and error handling
- Centralized error reporting and logging
- Visual feedback for retry attempts

## Phase 3: Cross-Platform Offline Testing

### Linux Testing Environment

- **Headless operation** using Xvfb or similar virtual display
- **Mock automation interfaces** that simulate Windows API calls
- **Image comparison testing** using stored game state screenshots
- **Configuration validation** without requiring actual game

### Windows Testing Environment

- **Sandbox mode** that doesn't interact with actual game
- **Recorded input playback** for consistent test scenarios
- **Automated screenshot comparison** for UI state verification
- **Performance benchmarking** for automation timing

### Test Structure

```text
tests/
├── offline/
│   ├── linux/
│   │   ├── test_config_validation.py
│   │   ├── test_strategy_simulation.py
│   │   └── test_image_processing.py
│   ├── windows/
│   │   ├── test_automation_playback.py
│   │   ├── test_ui_interaction.py
│   │   └── test_performance.py
│   └── common/
│       ├── test_json_schemas.py
│       └── test_error_handling.py
├── integration/
│   ├── test_map_configs.py
│   └── test_full_game_flow.py
└── test_data/
    ├── configs/
    ├── images/
    └── recordings/
```

## Phase 4: Advanced Features & Extensibility

### Dynamic Strategy Loading

- **Runtime config reloading** without restart
- **Strategy validation** before execution
- **A/B testing framework** for strategy comparison
- **Performance metrics collection**

### Enhanced Monkey Management

- **Multi-path upgrade strategies**
- **Ability usage optimization**
- **Resource management** (money, lives tracking)
- **Adaptive placement** based on game state

### Image Recognition Improvements

- **Machine learning integration** for better tower detection
- **Dynamic template updating** based on game version
- **Multi-scale template matching**
- **Real-time game state analysis**

## Phase 5: User Interface & Community Features

### Configuration GUI

- **Visual map editor** for placement coordinates
- **Drag-and-drop strategy builder**
- **Real-time preview** of automation sequences
- **Import/export** of configuration files

### Community Integration

- **Strategy sharing platform**
- **Automated strategy optimization**
- **Leaderboards and statistics**
- **Plugin system** for custom modules

## Technical Architecture Improvements

### Code Organization

```text
btd6_auto/
├── core/
│   ├── config/
│   │   ├── loaders.py
│   │   ├── validators.py
│   │   └── managers.py
│   ├── automation/
│   │   ├── input_simulator.py
│   │   ├── image_processor.py
│   │   └── retry_handler.py
│   ├── strategy/
│   │   ├── executor.py
│   │   ├── optimizer.py
│   │   └── analyzer.py
│   └── recovery/
│       ├── error_handler.py
│       └── state_recoverer.py
├── platform/
│   ├── windows/
│   │   ├── window_manager.py
│   │   └── input_handler.py
│   └── linux/
│       ├── virtual_display.py
│       └── mock_interfaces.py
├── configs/
│   ├── maps/
│   └── global.json
└── tests/
    └── offline/
```

### Performance Optimizations

- **Async/await patterns** for non-blocking operations
- **Connection pooling** for image processing
- **Caching layer** for configuration and templates
- **Memory management** for large screenshot handling

## Migration Strategy

### Phase 1 Migration (Current → Map-Specific Configs)

1. Create new configuration system alongside existing
2. Migrate hardcoded values to JSON format
3. Update core modules to use new config system
4. Maintain backward compatibility during transition
5. Deprecate old configuration approach

### Testing Migration

1. Create offline test framework first
2. Migrate existing tests to new structure
3. Add comprehensive regression tests
4. Implement continuous integration pipeline

## Success Metrics

### Technical Metrics

- **Configuration load time** < 100ms
- **Image recognition accuracy** > 95%
- **Retry success rate** > 90%
- **Cross-platform test coverage** > 80%

### User Experience Metrics

- **Setup time** for new maps < 5 minutes
- **Strategy configuration time** < 10 minutes
- **Error recovery time** < 30 seconds
- **Documentation completeness** > 90%

## Risk Mitigation

### Technical Risks

- **Game updates breaking image recognition** → Template auto-update system
- **Performance degradation** → Profiling and optimization phases
- **Platform compatibility issues** → Comprehensive testing strategy

### Project Risks

- **Scope creep** → Strict phase-based development approach
- **Resource constraints** → Modular design allowing incremental delivery
- **Community expectations** → Clear roadmap communication

## Timeline Estimate

- **Phase 1 (Config System)**: 2-3 weeks
- **Phase 2 (Error Handling)**: 1-2 weeks
- **Phase 3 (Offline Testing)**: 2-3 weeks
- **Phase 4 (Advanced Features)**: 3-4 weeks
- **Phase 5 (UI & Community)**: 4-6 weeks

*Total estimated timeline: 12-18 weeks depending on development pace and testing requirements.*

---

This roadmap provides a comprehensive plan for evolving the BTD6 Automation Bot from MVP to a robust, production-ready automation system. Each phase builds upon the previous, ensuring steady progress toward the final vision.
