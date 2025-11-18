"""
Unit tests for try_targeting_success helper in monkey_manager.py
"""

from btd6_auto.monkey_manager import try_targeting_success


def dummy_action():
    pass


def always_fail_confirm(pre, post, threshold):
    return False, 0.0


def region1_success_confirm(pre, post, threshold):
    # Only region 1 will succeed
    if pre == "region1" and post == "region1":
        return True, 90.0
    return False, 0.0


def region2_success_confirm(pre, post, threshold):
    # Only region 2 will succeed
    if pre == "region2" and post == "region2":
        return True, 90.0
    return False, 0.0


def both_success_confirm(pre, post, threshold):
    return True, 90.0


def test_try_targeting_success_region1(monkeypatch):
    """
    Test try_targeting_success when only region1 succeeds.
    Expected: Returns True when region1 is confirmed as successful.
    """
    monkeypatch.setattr(
        "btd6_auto.monkey_manager.capture_region",
        lambda region: region
        if region in ("region1", "region2")
        else "other",
    )
    result = try_targeting_success(
        (1, 2),  # coords
        "region1",  # targeting_region_1
        "region2",  # targeting_region_2
        85.0,  # targeting_threshold
        2,  # max_attempts
        0.05,  # delay
        region1_success_confirm,  # confirm_fn
    )
    assert result is True


def test_try_targeting_success_region2(monkeypatch):
    """
    Test try_targeting_success when only region2 succeeds.
    Expected: Returns True when region2 is confirmed as successful.
    """
    monkeypatch.setattr(
        "btd6_auto.monkey_manager.capture_region", lambda region: "region2"
    )
    result = try_targeting_success(
        (1, 2),
        "region1",
        "region2",
        85.0,
        2,
        0.01,
        region2_success_confirm,
    )
    assert result is True


def test_try_targeting_success_both(monkeypatch):
    """
    Test try_targeting_success when both regions succeed.
    Expected: Returns True when confirmation always succeeds.
    """
    monkeypatch.setattr(
        "btd6_auto.monkey_manager.capture_region", lambda region: "any"
    )
    result = try_targeting_success(
        (1, 2),
        "region1",
        "region2",
        85.0,
        2,
        0.01,
        both_success_confirm,
    )
    assert result is True


def test_try_targeting_success_fail(monkeypatch):
    """
    Test try_targeting_success when confirmation always fails.
    Expected: Returns False when no region is confirmed as successful.
    """
    monkeypatch.setattr(
        "btd6_auto.monkey_manager.capture_region", lambda region: "none"
    )
    result = try_targeting_success(
        (1, 2),
        "region1",
        "region2",
        85.0,
        2,
        0.01,
        always_fail_confirm,
    )
    assert result is False


def test_try_targeting_success_exception(monkeypatch):
    """
    Test try_targeting_success when capture_region raises an exception.
    Expected: Returns False when an exception occurs during region capture.
    """

    def raise_exception(region):
        raise Exception("fail")

    monkeypatch.setattr(
        "btd6_auto.monkey_manager.capture_region", raise_exception
    )
    result = try_targeting_success(
        (1, 2),
        "region1",
        "region2",
        85.0,
        2,
        0.01,
        always_fail_confirm,
    )
    assert result is False
