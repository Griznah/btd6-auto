# Plan: Vision-Based Error Handling for Monkey Selection/Placement

Add robust error handling to monkey selection and placement by verifying actions using image recognition (OpenCV). This ensures the bot can detect and recover from failed selections/placements, since direct game state access is unavailable. We only support 1920x1080 resolution. Testing will reveal thresholds.

## Steps

1. Integrate `find_element_on_screen` from [`vision.py`](btd6_auto/vision.py) to verify monkey/hero selection and placement.
2. For selection of monkeys/towers and hero before doing placement:
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
   - After expected placement, click tower and use vision to confirm the monkey/hero appears at the intended location. When selecting a tower, the areas at either (Top Left: {X: 35, Y:65} Bottom Right: {X:415, Y:940}) or (Top Left: {X: 1260, Y:60} Bottom Right: {X:1635, Y:940}) has at least a 85% change. Make this a seperate function called confirm_selection()
   - Retry placement or log error if confirmation fails. Log each attempt with threshold.
4. Add configurable retry logic and delays, using global config for max attempts and timing.
5. Log all failures and recovery attempts for debugging and reliability.

### Considerations

1. **Centralize Vision Logic in `vision.py`:**
   - Move all image comparison, region capture, and difference calculation functions to `vision.py`.
   - Expose high-level functions like `verify_placement_change(pre_img, post_img, region, threshold)` and `capture_region(region)`.

2. **Simplify Placement Functions in `monkey_manager.py`:**
   - `place_monkey` and `place_hero` should only handle input actions and call vision helpers for validation.
   - After placement, call `vision.py` functions to confirm success and handle retries.

3. **Configurable Parameters:**
   - Store thresholds, retry limits, and region coordinates in `global.json` for easy tuning

4. **Consistent Logging:**
   - Ensure all vision-related logging (difference values, errors, retries) is handled in `vision.py` for uniformity.

5. **Testing and Extensibility:**
   - Design vision functions to be easily testable and reusable for other game actions (e.g., upgrades, ability use).

### Further Considerations

1. **Separation of Concerns:** Keep input automation and vision validation strictly separated for easier debugging and future extension.
2. **Error Escalation:** Add a generic error handler in `vision.py` for repeated failures, which can be called from any module.
3. **Documentation:** Document all vision helper functions with expected input/output and edge case handling, following PEP8.
4. **Error Handling:**  After max retries have reached we clean up all threads and loops and quit our program.
