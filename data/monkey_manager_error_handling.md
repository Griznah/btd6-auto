# Plan: Vision-Based Error Handling for Monkey Selection/Placement

Add robust error handling to monkey selection and placement by verifying actions using image recognition (OpenCV). This ensures the bot can detect and recover from failed selections/placements, since direct game state access is unavailable. We only support 1920x1080 resolution. Testing will reveal thresholds.

## Steps

1. Integrate `find_element_on_screen` from [`vision.py`](btd6_auto/vision.py) to verify monkey/hero selection and placement.
2. Update `select_monkey` and `select_hero` in [`monkey_manager.py`](btd6_auto/monkey_manager.py) to:
   - Use vision to confirm selection: detect change on screen in area.
     1. Move cursor to {X: 1035, Y: 900}.
     2. Capture screen rectangle: Top Left: {Cursor X-100, Cursor Y-100}, Bottom Right: {Cursor X+100, Cursor Y+50}
     3. Attempt selection via hotkey.
     4. Capture screen again using same area
     5. Compare the two pictures to check if there is at least a 40% difference. Log each attempt with detected difference.
   - Retry and log error if selection not confirmed.
3. Update `place_monkey` and `place_hero` to:
   - Move cursor to desired location
   - Make sure the circle around the tower/cursor is not red
   - Try to mouse click the tower into place
   - After placement, click tower and use vision to confirm the monkey/hero appears at the intended location. When selecting a tower, the areas at either (Top Left: {X: 35, Y:65} Bottom Right: {X:415, Y:940}) or (Top Left: {X: 1260, Y:60} Bottom Right: {X:1635, Y:940}) has at least a 85% change.
   - Retry placement or log error if confirmation fails. Log each attempt with threshold.
4. Add configurable retry logic and delays, using global config for max attempts and timing.
5. Log all failures and recovery attempts for debugging and reliability.

### Further Considerations

1. What visual cues reliably indicate selection/placement?
   - Use OpenCV `absdiff`. We start with a 40% difference.
   - Placement: Difference is at least 85% within the mentioned area.
2. Should retries be limited, or escalate to a higher-level error handler?
   - Configurable sane amount of retries, no more than 5.
3. We only support 1920x1080 resolution
