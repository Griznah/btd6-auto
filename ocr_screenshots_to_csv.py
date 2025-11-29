"""
Script to run OCR on all PNG images in the top-level screenshots directory and save results as CSV.
Whitelists only digits for OCR. Output is saved to data/screenshots_ocr.csv.
"""

import os
import csv
import logging
import pytesseract
from PIL import Image


def ocr_digits_from_image(image_path):
    """
    Run pytesseract OCR on the image, whitelisting only digits.
    Returns the recognized string (digits only, as string), and processing time in seconds.
    """
    import time

    start_time = time.time()
    try:
        img = Image.open(image_path)
        custom_config = r"--psm 7 -c tessedit_char_whitelist=0123456789$,"
        text = pytesseract.image_to_string(img, config=custom_config)
        digits = text.strip().replace(",", "").replace("$", "")
        digits2 = "".join(filter(str.isdigit, text))
        duration = time.time() - start_time
        return digits, digits2, duration
    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"ERROR: {e}"
        return error_msg, error_msg, duration


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    screenshots_dir = os.path.join(os.path.dirname(__file__), "screenshots")
    output_csv = os.path.join(os.path.dirname(__file__), "data", "screenshots_ocr.csv")
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    rows = []
    for fname in os.listdir(screenshots_dir):
        if fname.lower().endswith(".png") and os.path.isfile(
            os.path.join(screenshots_dir, fname)
        ):
            img_path = os.path.join(screenshots_dir, fname)
            digits, digits2, duration = ocr_digits_from_image(img_path)
            rows.append((fname, digits, digits2))
            logging.info(f"Processed {fname}: {digits} (time: {duration:.3f}s)")
    with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "digits_strip", "digits_filter"])
        writer.writerows(rows)
    print(f"OCR results saved to {output_csv}")


if __name__ == "__main__":
    main()
