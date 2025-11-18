"""
Unit tests for try_targeting_success helper in monkey_manager.py
"""

from btd6_auto.monkey_manager import try_targeting_success


def dummy_action():
    """
    No-op placeholder action used in tests.
    
    This function performs no operation and exists as a stand-in where a callable is required.
    """
    pass


def always_fail_confirm(pre, post, threshold):
    """
    Always indicates that the confirmation failed and provides zero confidence.
    
    Returns:
        tuple: `(False, 0.0)` where the first element is `False` indicating failure and the second is the confidence score `0.0`.
    """
    return False, 0.0


def region1_success_confirm(pre, post, threshold):
    # Only region 1 will succeed
    """
    Confirm success for region1 based on captured pre/post region identifiers.
    
    Parameters:
        pre (str): Identifier captured before the action.
        post (str): Identifier captured after the action.
        threshold (float): Confidence threshold for confirmation.
    
    Returns:
        tuple: `(True, 90.0)` if both `pre` and `post` are `"region1"`, ` (False, 0.0)` otherwise.
    """
    if pre == "region1" and post == "region1":
        return True, 90.0
    return False, 0.0


def region2_success_confirm(pre, post, threshold):
    # Only region 2 will succeed
    """
    Confirm success for region2 based on pre- and post-capture identifiers.
    
    Parameters:
        pre (str): Identifier captured before the action.
        post (str): Identifier captured after the action.
        threshold (float): Confidence threshold (unused by this helper).
    
    Returns:
        (bool, float): `True` and a confidence score of 90.0 if both `pre` and `post` equal "region2"; `False` and 0.0 otherwise.
    """
    if pre == "region2" and post == "region2":
        return True, 90.0
    return False, 0.0


def both_success_confirm(pre, post, threshold):
    """
    Always confirms success for both regions with a fixed confidence score.
    
    Parameters:
        pre (str): Pre-action region identifier (unused).
        post (str): Post-action region identifier (unused).
        threshold (float): Confidence threshold (unused).
    
    Returns:
        tuple: `(True, 90.0)` where `True` indicates success and `90.0` is the confidence score.
    """
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
        """
        Always raises Exception("fail") to simulate a failure when capturing a region.
        
        Parameters:
            region: The region argument (ignored).
        
        Raises:
            Exception: Always raised with message "fail".
        """
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