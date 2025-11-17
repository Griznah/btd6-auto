import pytest
from btd6_auto.vision import rect_to_region


class TestRectToRegion:
    def test_valid_conversion(self):
        assert rect_to_region((10, 20, 110, 220)) == (10, 20, 100, 200)
        assert rect_to_region([0, 0, 1920, 1080]) == (0, 0, 1920, 1080)

    def test_invalid_length(self):
        with pytest.raises(ValueError):
            rect_to_region((10, 20, 30))
        with pytest.raises(ValueError):
            rect_to_region((10, 20, 30, 40, 50))

    def test_negative_width_height(self):
        with pytest.raises(ValueError):
            rect_to_region((100, 100, 50, 150))  # width negative
        with pytest.raises(ValueError):
            rect_to_region((100, 100, 150, 50))  # height negative

    def test_zero_width_height(self):
        with pytest.raises(ValueError):
            rect_to_region((10, 10, 10, 20))  # zero width
        with pytest.raises(ValueError):
            rect_to_region((10, 10, 20, 10))  # zero height
