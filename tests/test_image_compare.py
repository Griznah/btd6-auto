import cv2
import numpy as np
import logging
import os


def compare_images(img_path1, img_path2, threshold=30):
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ImageCompare")

    # Load images
    img1 = cv2.imread(img_path1)
    img2 = cv2.imread(img_path2)

    if img1 is None or img2 is None:
        logger.error(f"Could not load images: {img_path1}, {img_path2}")
        return False

    # Ensure images are the same size
    if img1.shape != img2.shape:
        logger.error(f"Image shapes differ: {img1.shape} vs {img2.shape}")
        return False

    # Compute absolute difference
    diff = cv2.absdiff(img1, img2)
    diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    nonzero_count = np.count_nonzero(diff_gray > threshold)
    total_pixels = diff_gray.size
    percent_diff = (nonzero_count / total_pixels) * 100

    logger.info(f"Total pixels: {total_pixels}")
    logger.info(f"Pixels above threshold ({threshold}): {nonzero_count}")
    logger.info(f"Percent difference: {percent_diff:.2f}%")

    # Optionally save diff image for inspection
    diff_path = os.path.join(os.path.dirname(img_path1), "diff.png")
    cv2.imwrite(diff_path, diff)
    logger.info(f"Diff image saved to: {diff_path}")

    return percent_diff


if __name__ == "__main__":
    img1 = os.path.join("tests", "images", "pre_monkey.png")
    img2 = os.path.join("tests", "images", "post_monkey.png")
    compare_images(img1, img2)

    # Template matching test
    logging.info("Starting template matching test...")
    img_full = cv2.imread(img2)
    img_template = cv2.imread(img1)
    if img_full is None or img_template is None:
        logging.error(
            f"Could not load images for template matching: {img2}, {img1}"
        )
    else:
        # Convert to grayscale for template matching
        img_full_gray = cv2.cvtColor(img_full, cv2.COLOR_BGR2GRAY)
        img_template_gray = cv2.cvtColor(img_template, cv2.COLOR_BGR2GRAY)
        res = cv2.matchTemplate(
            img_full_gray, img_template_gray, cv2.TM_CCOEFF_NORMED
        )
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        logging.info(f"Template matching max value: {max_val}")
        logging.info(f"Template matching location: {max_loc}")
        # Draw rectangle on match
        h, w = img_template_gray.shape
        img_matched = img_full.copy()
        cv2.rectangle(
            img_matched,
            max_loc,
            (max_loc[0] + w, max_loc[1] + h),
            (0, 255, 0),
            2,
        )
        matched_path = os.path.join(os.path.dirname(img2), "matched.png")
        cv2.imwrite(matched_path, img_matched)
        logging.info(f"Matched image saved to: {matched_path}")
