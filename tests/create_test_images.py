import cv2
import numpy as np
import os

def create_test_images():
    """Create synthetic test images for template matching tests."""

    # Create output directory
    output_dir = "/home/griznah/repos/btd6-auto/tests/test_data/images"
    os.makedirs(output_dir, exist_ok=True)

    # Create a simple button-like template (100x50 white rectangle with black border)
    button_template = np.zeros((50, 100, 3), dtype=np.uint8)
    button_template.fill(255)  # White background

    # Add black border
    cv2.rectangle(button_template, (0, 0), (99, 49), (0, 0, 0), 2)

    # Add "PLAY" text simulation (simple lines)
    cv2.line(button_template, (20, 25), (35, 25), (0, 0, 0), 2)  # P
    cv2.line(button_template, (40, 15), (40, 35), (0, 0, 0), 2)  # L
    cv2.line(button_template, (45, 25), (60, 25), (0, 0, 0), 2)  # A
    cv2.line(button_template, (65, 15), (65, 35), (0, 0, 0), 2)  # Y

    cv2.imwrite(os.path.join(output_dir, "button_play_test.png"), button_template)

    # Create a circular template (like a monkey head)
    circle_template = np.zeros((40, 40, 3), dtype=np.uint8)
    circle_template.fill(200)  # Light gray background
    cv2.circle(circle_template, (20, 20), 15, (100, 100, 100), -1)  # Dark gray circle
    cv2.circle(circle_template, (20, 20), 10, (255, 255, 255), -1)  # White inner circle

    cv2.imwrite(os.path.join(output_dir, "circle_template.png"), circle_template)

    # Create a rectangular template (like a UI element)
    rect_template = np.zeros((30, 60, 3), dtype=np.uint8)
    rect_template.fill(150)  # Medium gray background
    cv2.rectangle(rect_template, (5, 5), (55, 25), (255, 255, 255), -1)  # White rectangle

    cv2.imwrite(os.path.join(output_dir, "rect_template.png"), rect_template)

    # Create a test screenshot background (simulating game screen)
    screenshot = np.zeros((800, 1200, 3), dtype=np.uint8)
    screenshot.fill(50)  # Dark background

    # Add some UI elements to simulate game interface
    # Top menu bar
    cv2.rectangle(screenshot, (0, 0), (1200, 60), (100, 100, 100), -1)

    # Left sidebar
    cv2.rectangle(screenshot, (0, 60), (200, 800), (80, 80, 80), -1)

    # Game area (main play area)
    cv2.rectangle(screenshot, (200, 60), (1200, 800), (60, 120, 60), -1)

    # Add the button template to simulate a play button
    button_y, button_x = 300, 500
    screenshot[button_y:button_y+50, button_x:button_x+100] = button_template

    # Add circle template to simulate game objects
    circle_y, circle_x = 200, 900
    screenshot[circle_y:circle_y+40, circle_x:circle_x+40] = circle_template

    cv2.imwrite(os.path.join(output_dir, "test_screenshot.png"), screenshot)

    print(f"Created test images in {output_dir}")

if __name__ == "__main__":
    create_test_images()
