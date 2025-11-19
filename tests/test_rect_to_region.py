import pytest
from btd6_auto.vision import rect_to_region


class TestRectToRegion:
    """
    Unit tests for the rect_to_region function in btd6_auto.vision.
    These tests cover valid conversions, invalid input lengths, negative and zero dimensions.
    """

    def test_valid_conversion(self):
        """
        Test that valid rectangle inputs are correctly converted to region tuples.
        Expected: (x, y, width, height) where width and height are positive.
        """
        assert rect_to_region((10, 20, 110, 220)) == (10, 20, 100, 200)
        assert rect_to_region([0, 0, 1920, 1080]) == (0, 0, 1920, 1080)

    def test_invalid_length(self):
        """
        Test that ValueError is raised for input tuples/lists with invalid length.
        Expected: Exception for length != 4.
        """
        with pytest.raises(ValueError):
            rect_to_region((10, 20, 30))
        with pytest.raises(ValueError):
            rect_to_region((10, 20, 30, 40, 50))

    def test_negative_width_height(self):
        """
        Test that ValueError is raised when width or height is negative.
        Expected: Exception for negative width or height.
        """
        with pytest.raises(ValueError):
            rect_to_region((100, 100, 50, 150))  # width negative
        with pytest.raises(ValueError):
            rect_to_region((100, 100, 150, 50))  # height negative

    def test_zero_width_height(self):
        """
        Test that ValueError is raised when width or height is zero.
        Expected: Exception for zero width or height.
        """
        with pytest.raises(ValueError):
            rect_to_region((10, 10, 10, 20))  # zero width
        with pytest.raises(ValueError):
            rect_to_region((10, 10, 20, 10))  # zero height
