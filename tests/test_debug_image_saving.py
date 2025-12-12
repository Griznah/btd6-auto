"""
Unit tests for debug image saving functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import os
import tempfile
import shutil
from datetime import datetime

# Import the functions to test
from btd6_auto.vision import save_debug_image, cleanup_debug_images


class TestDebugImageSaving(unittest.TestCase):
    """Test cases for debug image saving functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        self.test_prefix = "test_prefix"
        self.test_subfolder = "test_subfolder"
        self.test_base_folder = tempfile.mkdtemp(prefix="debug_test_")

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_base_folder):
            shutil.rmtree(self.test_base_folder)

    def test_save_debug_image_basic(self):
        """Test basic save_debug_image functionality."""
        filepath = save_debug_image(
            self.test_image,
            self.test_prefix,
            base_folder=self.test_base_folder
        )

        # Check that file was created
        self.assertTrue(os.path.exists(filepath))

        # Check folder structure
        date_str = datetime.now().strftime("%Y-%m-%d")
        expected_folder = os.path.join(self.test_base_folder, date_str)
        self.assertTrue(os.path.exists(expected_folder))

        # Check filename format
        filename = os.path.basename(filepath)
        self.assertTrue(filename.startswith(f"{self.test_prefix}_"))
        self.assertTrue(filename.endswith(".png"))

    def test_save_debug_image_with_subfolder(self):
        """Test save_debug_image with subfolder."""
        filepath = save_debug_image(
            self.test_image,
            self.test_prefix,
            subfolder=self.test_subfolder,
            base_folder=self.test_base_folder
        )

        # Check that subfolder was created
        date_str = datetime.now().strftime("%Y-%m-%d")
        expected_folder = os.path.join(self.test_base_folder, date_str, self.test_subfolder)
        self.assertTrue(os.path.exists(expected_folder))

        # Check filepath contains subfolder
        self.assertIn(self.test_subfolder, filepath)

    def test_save_debug_image_none_input(self):
        """Test save_debug_image with None image."""
        filepath = save_debug_image(
            None,
            self.test_prefix,
            base_folder=self.test_base_folder
        )

        # Should return None for None input
        self.assertIsNone(filepath)

    @patch('cv2.imwrite')
    def test_save_debug_image_cv2_error(self, mock_imwrite):
        """Test save_debug_image when cv2.imwrite fails."""
        mock_imwrite.return_value = False

        filepath = save_debug_image(
            self.test_image,
            self.test_prefix,
            base_folder=self.test_base_folder
        )

        # Still returns filepath even if save fails (cv2.imwrite doesn't raise)
        self.assertIsNotNone(filepath)

    def test_save_debug_image_unique_filenames(self):
        """Test that save_debug_image creates unique filenames."""
        filepath1 = save_debug_image(
            self.test_image,
            self.test_prefix,
            base_folder=self.test_base_folder
        )

        # Small delay to ensure different timestamp
        import time
        time.sleep(0.001)

        filepath2 = save_debug_image(
            self.test_image,
            self.test_prefix,
            base_folder=self.test_base_folder
        )

        # Filepaths should be different
        self.assertNotEqual(filepath1, filepath2)

        # Both files should exist
        self.assertTrue(os.path.exists(filepath1))
        self.assertTrue(os.path.exists(filepath2))

    def test_cleanup_debug_images(self):
        """Test cleanup_debug_images functionality with real folders."""
        from datetime import datetime, timedelta

        # Create test folder structure
        old_date = datetime.now() - timedelta(days=14)  # 14 days ago
        new_date = datetime.now()  # Today

        old_folder = os.path.join(self.test_base_folder, old_date.strftime("%Y-%m-%d"))
        new_folder = os.path.join(self.test_base_folder, new_date.strftime("%Y-%m-%d"))

        # Create folders and files
        os.makedirs(old_folder, exist_ok=True)
        os.makedirs(new_folder, exist_ok=True)

        with open(os.path.join(old_folder, "old_file.png"), 'w') as f:
            f.write("test")

        with open(os.path.join(new_folder, "new_file.png"), 'w') as f:
            f.write("test")

        # Verify both folders exist
        self.assertTrue(os.path.exists(old_folder))
        self.assertTrue(os.path.exists(new_folder))

        # Run cleanup with 7 day retention
        cleanup_debug_images(base_folder=self.test_base_folder, retention_days=7)

        # Old folder should be deleted, new folder should remain
        self.assertFalse(os.path.exists(old_folder))
        self.assertTrue(os.path.exists(new_folder))

    def test_cleanup_debug_images_invalid_folder(self):
        """Test cleanup_debug_images with invalid folder names."""
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [
                ("debug/upgrades/invalid_date", [], ["file.png"]),
            ]

            with patch('os.path.basename') as mock_basename:
                mock_basename.return_value = "invalid_date"

                # Should not raise exception
                cleanup_debug_images(base_folder=self.test_base_folder, retention_days=7)

    def test_cleanup_debug_images_no_folder(self):
        """Test cleanup_debug_images when debug folder doesn't exist."""
        # Should not raise exception
        cleanup_debug_images(
            base_folder=os.path.join(self.test_base_folder, "nonexistent"),
            retention_days=7
        )


class TestDebugImageIntegration(unittest.TestCase):
    """Integration tests for debug functionality with upgrade actions."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_base_folder = tempfile.mkdtemp(prefix="debug_integration_test_")
        self.debug_config = {
            "save_images": True,
            "save_on_success": True,
            "save_on_failure": True,
            "save_on_retry": True,
            "base_folder": self.test_base_folder
        }

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_base_folder):
            shutil.rmtree(self.test_base_folder)

    @patch('btd6_auto.vision.capture_region')
    def test_debug_image_saving_workflow(self, mock_capture):
        """Test the complete debug image saving workflow."""
        # Setup mock capture
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_capture.return_value = test_image

        # Simulate multiple captures
        captures = []

        # Pre-targeting image
        filepath1 = save_debug_image(
            test_image,
            "pre_targeting_test_tower_path_1",
            "targeting",
            self.test_base_folder
        )
        captures.append(filepath1)

        # Targeting success image
        filepath2 = save_debug_image(
            test_image,
            "targeting_success_test_tower_path_1",
            "targeting",
            self.test_base_folder
        )
        captures.append(filepath2)

        # Verification images
        filepath3 = save_debug_image(
            test_image,
            "pre_upgrade_attempt_0_test_tower_path_1",
            "verification",
            self.test_base_folder
        )
        captures.append(filepath3)

        filepath4 = save_debug_image(
            test_image,
            "post_upgrade_attempt_0_test_tower_path_1",
            "verification",
            self.test_base_folder
        )
        captures.append(filepath4)

        # Verify all files were created
        for filepath in captures:
            self.assertTrue(os.path.exists(filepath), f"File not created: {filepath}")

        # Verify folder structure
        date_str = datetime.now().strftime("%Y-%m-%d")
        for subfolder in ["targeting", "verification"]:
            folder_path = os.path.join(self.test_base_folder, date_str, subfolder)
            self.assertTrue(os.path.exists(folder_path), f"Folder not created: {folder_path}")


if __name__ == '__main__':
    unittest.main()