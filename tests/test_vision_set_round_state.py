"""
Unit tests for set_round_state in vision.py
"""
import sys
import os
from unittest import mock

# Ensure btd6_auto is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from btd6_auto import vision


def mock_find_in_region_factory(success_on_attempt=1):
    """Returns a mock find_in_region that succeeds on the Nth call."""
    call_count = {'count': 0}
    def _mock(template_path):
        call_count['count'] += 1
        return call_count['count'] >= success_on_attempt
    return _mock


@mock.patch('btd6_auto.vision.keyboard')
def test_set_round_state_fast_success(mock_keyboard):
    # find_in_region succeeds on first try
    assert vision.set_round_state('fast', find_in_region=mock_find_in_region_factory(1)) is True
    mock_keyboard.press_and_release.assert_not_called()  # Already fast


@mock.patch('btd6_auto.vision.keyboard')
def test_set_round_state_fast_retry(mock_keyboard):
    # find_in_region succeeds on 2nd try
    call_count = {'count': 0}
    def _mock(template_path):
        call_count['count'] += 1
        return call_count['count'] == 2
    assert vision.set_round_state('fast', find_in_region=_mock) is True
    assert mock_keyboard.press_and_release.call_count == 1


@mock.patch('btd6_auto.vision.keyboard')
def test_set_round_state_slow_failure(mock_keyboard):
    # find_in_region always fails
    assert vision.set_round_state('slow', max_retries=2, find_in_region=lambda x: False) is False
    assert mock_keyboard.press_and_release.call_count == 2


@mock.patch('btd6_auto.vision.keyboard')
def test_set_round_state_start_success(mock_keyboard):
    # find_in_region returns True for start and fast
    def _mock(template_path):
        if 'start' in template_path:
            return True
        if 'fast' in template_path:
            return True
        return False
    assert vision.set_round_state('start', find_in_region=_mock) is True
    mock_keyboard.press_and_release.assert_not_called()

@mock.patch('btd6_auto.vision.keyboard')
def test_set_round_state_invalid(mock_keyboard):
    assert vision.set_round_state('invalid') is False
