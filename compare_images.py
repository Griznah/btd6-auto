#!/usr/bin/env python3
"""
Standalone image comparison script for BTD6 Auto.

Based on confirm_selection() from btd6_auto/vision.py
"""

import argparse
import logging
import os
import sys
import cv2
import numpy as np


def calculate_image_difference(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Compute the percentage of differing pixels between two images.

    This is extracted from btd6_auto/vision.py for standalone use.

    Args:
        img1: First image as numpy array (BGR format)
        img2: Second image as numpy array (BGR format)

    Returns:
        float: Percentage of pixels that differ between the images

    Raises:
        ValueError: If image shapes do not match
    """
    if img1.shape != img2.shape:
        raise ValueError(
            f"Image shapes do not match for comparison: {img1.shape} vs {img2.shape}"
        )

    diff = cv2.absdiff(img1, img2)
    nonzero = np.count_nonzero(diff)
    total = diff.size
    percent_diff = (nonzero / total) * 100

    return percent_diff


def compare_images(
    img_path1: str, img_path2: str, threshold: float = 20.0, save_diff_path: str = None
) -> tuple[bool, float]:
    """
    Compare two images and determine if the difference meets the threshold.

    Based on confirm_selection() from btd6_auto/vision.py.

    Args:
        img_path1: Path to the first image
        img_path2: Path to the second image
        threshold: Minimum percent difference to consider as "different" (default: 40.0)
        save_diff_path: Optional path to save the difference image

    Returns:
        tuple: (bool indicating if difference >= threshold, actual percentage difference)
    """
    # Validate input files exist
    if not os.path.exists(img_path1):
        raise FileNotFoundError(f"Image file not found: {img_path1}")
    if not os.path.exists(img_path2):
        raise FileNotFoundError(f"Image file not found: {img_path2}")

    # Load images
    img1 = cv2.imread(img_path1)
    img2 = cv2.imread(img_path2)

    if img1 is None:
        raise ValueError(f"Could not read image file: {img_path1}")
    if img2 is None:
        raise ValueError(f"Could not read image file: {img_path2}")

    # Calculate difference
    percent_diff = calculate_image_difference(img1, img2)

    # Save difference image if requested
    if save_diff_path:
        diff = cv2.absdiff(img1, img2)
        cv2.imwrite(save_diff_path, diff)
        logging.info(f"Difference image saved to: {save_diff_path}")

    return percent_diff >= threshold, percent_diff


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s", datefmt="%H:%M:%S")


def color_print(text: str, color: str = None):
    """Print text with optional color formatting."""
    if not sys.stdout.isatty():  # No color if output is redirected
        print(text)
        return

    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m",
    }

    if color and color in colors:
        print(f"{colors[color]}{text}{colors['reset']}")
    else:
        print(text)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Compare two images and report percentage difference",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s image1.png image2.png
  %(prog)s before.png after.png --threshold 50.0
  %(prog)s image1.png image2.png --save-diff diff.png
  %(prog)s image1.png image2.png --verbose
        """,
    )

    parser.add_argument("image1", help="Path to the first image")

    parser.add_argument("image2", help="Path to the second image")

    parser.add_argument(
        "--threshold",
        type=float,
        default=20.0,
        help='Minimum percent difference to consider as "different" (default: 20.0)',
    )

    parser.add_argument(
        "--save-diff", metavar="PATH", help="Save the difference image to the specified path"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    try:
        logging.debug(f"Comparing '{args.image1}' with '{args.image2}'")
        logging.debug(f"Threshold: {args.threshold}%")

        # Compare images
        meets_threshold, percent_diff = compare_images(
            args.image1, args.image2, args.threshold, args.save_diff
        )

        # Output results
        print(f"\nImage Difference: {percent_diff:.2f}%")
        print(f"Threshold: {args.threshold:.2f}%")

        if meets_threshold:
            color_print("\n[*] Images are SIGNIFICANTLY different", color="green")
        else:
            color_print("\n[-] Images are NOT significantly different", color="yellow")

        # Return appropriate exit code
        sys.exit(0 if meets_threshold else 1)

    except FileNotFoundError as e:
        color_print(f"Error: {e}", color="red")
        sys.exit(2)
    except ValueError as e:
        color_print(f"Error: {e}", color="red")
        sys.exit(3)
    except Exception as e:
        color_print(f"Unexpected error: {e}", color="red")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(4)


if __name__ == "__main__":
    main()
