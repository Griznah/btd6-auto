"""
Unit tests for run_upgrade_action() fixes.
Tests thread safety, resource management, state consistency, and error handling improvements.
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock, call
from btd6_auto.actions import ActionManager
from btd6_auto.exceptions import UpgradeStateError, UpgradeVerificationError, UpgradeActionError


class TestUpgradeActionThreadSafety:
    """Test thread safety of upgrade state access."""

    @pytest.fixture
    def action_manager(self):
        """Create an ActionManager instance for testing."""
        map_config = {"map_name": "Test Map", "actions": []}
        global_config = {"automation": {"timing": {}}}
        return ActionManager(map_config, global_config)

    def test_state_lock_initialized(self, action_manager):
        """Test that thread lock is properly initialized."""
        assert hasattr(action_manager, '_state_lock')
        assert hasattr(action_manager._state_lock, 'acquire')  # Check it has lock methods

    def test_state_access_context_manager(self, action_manager):
        """Test that _access_upgrade_state provides thread-safe access."""
        with action_manager._access_upgrade_state() as state:
            assert state == {}
            state["test_target"] = {"path_1": 1}

        # Verify state was updated
        with action_manager._access_upgrade_state() as state:
            assert state["test_target"] == {"path_1": 1}

    def test_concurrent_state_access(self, action_manager):
        """Test that concurrent access to upgrade state is thread-safe."""
        results = []
        errors = []

        def update_state(target_id):
            try:
                for i in range(10):
                    with action_manager._access_upgrade_state() as state:
                        target_key = f"target_{target_id}"
                        if target_key not in state:
                            state[target_key] = {"path_1": 0, "path_2": 0, "path_3": 0}
                        state[target_key]["path_1"] += 1
                    time.sleep(0.001)  # Small delay to increase chance of race conditions
                results.append(f"Thread {target_id} completed")
            except Exception as e:
                errors.append(f"Thread {target_id} error: {e}")

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=update_state, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5, f"Not all threads completed: {results}"

        # Verify final state is consistent
        with action_manager._access_upgrade_state() as state:
            for i in range(5):
                target_key = f"target_{i}"
                assert state[target_key]["path_1"] == 10, f"Inconsistent state for {target_key}"


class TestUpgradeActionValidation:
    """Test upgrade action validation improvements."""

    @pytest.fixture
    def action_manager_with_positions(self):
        """Create ActionManager with mock monkey positions."""
        map_config = {
            "map_name": "Test Map",
            "monkeys": [
                {"name": "Dart Monkey 01", "position": {"x": 100, "y": 200}},
                {"name": "Tack Shooter 01", "position": {"x": 300, "y": 400}}
            ]
        }
        global_config = {"automation": {"timing": {}}}
        return ActionManager(map_config, global_config)

    def test_validate_upgrade_action_success(self, action_manager_with_positions):
        """Test successful validation of upgrade action."""
        action = {
            "target": "Dart Monkey 01",
            "upgrade_path": {"path_1": 2}
        }

        target, path_key, requested = action_manager_with_positions._validate_upgrade_action(action)

        assert target == "Dart Monkey 01"
        assert path_key == "path_1"
        assert requested == 2

    def test_validate_upgrade_action_missing_target(self, action_manager_with_positions):
        """Test validation failure when target is missing."""
        action = {"upgrade_path": {"path_1": 2}}

        with pytest.raises(UpgradeStateError, match="missing target or upgrade_path"):
            action_manager_with_positions._validate_upgrade_action(action)

    def test_validate_upgrade_action_missing_path(self, action_manager_with_positions):
        """Test validation failure when upgrade_path is missing."""
        action = {"target": "Dart Monkey 01"}

        with pytest.raises(UpgradeStateError, match="missing target or upgrade_path"):
            action_manager_with_positions._validate_upgrade_action(action)

    def test_validate_upgrade_action_multiple_paths(self, action_manager_with_positions):
        """Test validation failure when multiple upgrade paths are specified."""
        action = {
            "target": "Dart Monkey 01",
            "upgrade_path": {"path_1": 1, "path_2": 1}
        }

        with pytest.raises(UpgradeStateError, match="must specify exactly one path"):
            action_manager_with_positions._validate_upgrade_action(action)

    def test_validate_upgrade_action_invalid_path_key(self, action_manager_with_positions):
        """Test validation failure with invalid path key."""
        action = {
            "target": "Dart Monkey 01",
            "upgrade_path": {"path_4": 1}
        }

        with pytest.raises(UpgradeStateError, match="Invalid path key 'path_4'"):
            action_manager_with_positions._validate_upgrade_action(action)

    def test_validate_upgrade_action_unknown_target(self, action_manager_with_positions):
        """Test validation failure when target is unknown."""
        action = {
            "target": "Unknown Tower",
            "upgrade_path": {"path_1": 1}
        }

        with pytest.raises(UpgradeStateError, match="No position found for tower"):
            action_manager_with_positions._validate_upgrade_action(action)


class TestUpgradeActionResourceManagement:
    """Test image capture resource management."""

    @pytest.fixture
    def action_manager(self):
        """Create an ActionManager instance for testing."""
        map_config = {"map_name": "Test Map", "actions": []}
        global_config = {"automation": {"timing": {}}}
        return ActionManager(map_config, global_config)

    def test_capture_context_manager_cleanup(self, action_manager):
        """Test that image capture context manager properly cleans up resources."""
        images_list = []

        with patch('btd6_auto.actions.capture_region') as mock_capture:
            mock_capture.return_value = Mock()

            # Test context manager with initial image
            with action_manager._capture_and_manage_images(None, Mock()) as images:
                images_list = images
                # Simulate adding images to the list
                images.append(Mock())
                images.append(Mock())

                # Verify images are in the list
                assert len(images) == 3

        # Verify list is cleared after context exits
        assert len(images_list) == 0

    def test_capture_context_manager_with_verification_region(self, action_manager):
        """Test context manager with verification region."""
        mock_region = Mock()
        mock_img = Mock()

        with patch('btd6_auto.actions.capture_region') as mock_capture:
            mock_capture.return_value = mock_img

            with action_manager._capture_and_manage_images(mock_region) as images:
                # Note: capture_region is not called in the context manager itself
                # but in the code that uses it
                assert len(images) == 0

            # Verify that images list is cleaned up after context exit
            assert len(images) == 0


class TestUpgradeActionStateConsistency:
    """Test state consistency fixes in upgrade actions."""

    @pytest.fixture
    def action_manager_with_fixtures(self):
        """Create ActionManager with necessary fixtures for testing."""
        from btd6_auto.currency_reader import CurrencyReader

        map_config = {
            "map_name": "Test Map",
            "monkeys": [{"name": "Dart Monkey 01", "position": {"x": 100, "y": 200}}],
            "actions": []
        }
        global_config = {
            "automation": {
                "timing": {"upgrade_delay": 0.01},
                "retries": {"max_retries": 1, "retry_delay": 0.01}
            },
            "hotkey": {
                "upgrade_path_1": "q",
                "upgrade_path_2": "w",
                "upgrade_path_3": "e"
            }
        }
        currency_reader = Mock(spec=CurrencyReader)
        return ActionManager(map_config, global_config, currency_reader=currency_reader)

    @patch('btd6_auto.actions.activate_btd6_window')
    @patch('btd6_auto.actions.try_targeting_success')
    @patch('btd6_auto.actions.keyboard.send')
    @patch('btd6_auto.actions.move_and_click')
    @patch('btd6_auto.actions.cursor_resting_spot')
    def test_state_only_updated_after_verification(self, mock_cursor_rest, mock_move_click,
                                                  mock_keyboard, mock_targeting, mock_activate,
                                                  action_manager_with_fixtures):
        """Test that state is only updated after successful verification."""
        # Setup targeting to succeed
        mock_target_img = Mock()
        mock_targeting.return_value = (True, "region1", mock_target_img)
        mock_cursor_rest.return_value = (0, 0)

        action = {
            "step": 1,
            "target": "Dart Monkey 01",
            "upgrade_path": {"path_1": 1}
        }

        # Mock verification to fail
        with patch.object(action_manager_with_fixtures, '_attempt_upgrade_verification') as mock_verify:
            mock_verify.side_effect = UpgradeVerificationError("Verification failed")

            # Action should raise exception
            with pytest.raises(UpgradeVerificationError):
                action_manager_with_fixtures.run_upgrade_action(action)

            # State should NOT be updated when verification fails
            with action_manager_with_fixtures._access_upgrade_state() as state:
                assert "Dart Monkey 01" not in state

    @patch('btd6_auto.actions.activate_btd6_window')
    @patch('btd6_auto.actions.try_targeting_success')
    @patch('btd6_auto.actions.keyboard.send')
    @patch('btd6_auto.actions.move_and_click')
    @patch('btd6_auto.actions.cursor_resting_spot')
    def test_state_updated_correctly_on_success(self, mock_cursor_rest, mock_move_click,
                                               mock_keyboard, mock_targeting, mock_activate,
                                               action_manager_with_fixtures):
        """Test that state is updated correctly on successful verification."""
        # Setup targeting to succeed
        mock_target_img = Mock()
        mock_targeting.return_value = (True, "region1", mock_target_img)
        mock_cursor_rest.return_value = (0, 0)

        action = {
            "step": 1,
            "target": "Dart Monkey 01",
            "upgrade_path": {"path_1": 1}
        }

        # Mock verification to succeed
        with patch.object(action_manager_with_fixtures, '_attempt_upgrade_verification') as mock_verify:
            mock_verify.return_value = (True, 20.0)

            # Run upgrade action
            action_manager_with_fixtures.run_upgrade_action(action)

            # State should be updated when verification succeeds
            with action_manager_with_fixtures._access_upgrade_state() as state:
                assert state["Dart Monkey 01"] == {"path_1": 1, "path_2": 0, "path_3": 0}

    @patch('btd6_auto.actions.activate_btd6_window')
    def test_partial_upgrade_not_marked_completed(self, mock_activate, action_manager_with_fixtures):
        """Test that partial upgrades (below requested tier) are not marked as completed."""
        # Set initial state to tier 1
        with action_manager_with_fixtures._access_upgrade_state() as state:
            state["Dart Monkey 01"] = {"path_1": 1, "path_2": 0, "path_3": 0}

        # Mock targeting and verification
        with patch('btd6_auto.actions.try_targeting_success') as mock_targeting:
            with patch.object(action_manager_with_fixtures, '_attempt_upgrade_verification') as mock_verify:
                with patch('btd6_auto.actions.move_and_click'):
                    with patch('btd6_auto.actions.cursor_resting_spot', return_value=(0, 0)):
                        mock_target_img = Mock()
                        mock_targeting.return_value = (True, "region1", mock_target_img)
                        mock_verify.return_value = (True, 20.0)

                        # Request tier 3, but verify only succeeds for tier 2
                        action = {
                            "step": 1,
                            "target": "Dart Monkey 01",
                            "upgrade_path": {"path_1": 3}
                        }

                        action_manager_with_fixtures.run_upgrade_action(action)

                        # State should be updated to tier 2
                        with action_manager_with_fixtures._access_upgrade_state() as state:
                            assert state["Dart Monkey 01"]["path_1"] == 2

                        # Step should NOT be marked completed
                        assert 1 not in action_manager_with_fixtures.completed_steps


class TestUpgradeActionErrorHandling:
    """Test enhanced error handling in upgrade actions."""

    @pytest.fixture
    def action_manager(self):
        """Create an ActionManager instance for testing."""
        from btd6_auto.currency_reader import CurrencyReader

        map_config = {"map_name": "Test Map", "actions": []}
        global_config = {
            "automation": {"timing": {}},
            "hotkey": {
                "upgrade_path_1": "q",
                "upgrade_path_2": "w",
                "upgrade_path_3": "e"
            }
        }
        currency_reader = Mock(spec=CurrencyReader)
        return ActionManager(map_config, global_config, currency_reader=currency_reader)

    @patch('btd6_auto.actions.activate_btd6_window')
    def test_validation_error_handling(self, mock_activate, action_manager):
        """Test that validation errors are properly raised and handled."""
        action = {
            "target": "Unknown Tower",
            "upgrade_path": {"path_1": 1}
        }

        with pytest.raises(UpgradeStateError):
            action_manager.run_upgrade_action(action)

    @patch('btd6_auto.actions.activate_btd6_window')
    @patch('btd6_auto.actions.try_targeting_success')
    def test_verification_error_handling(self, mock_targeting, mock_activate, action_manager):
        """Test that verification errors are properly raised and handled."""
        # Setup map with known tower
        action_manager.monkey_positions = {"Test Tower": (100, 200)}

        # Setup targeting to succeed but verification to fail
        mock_target_img = Mock()
        mock_targeting.return_value = (True, "region1", mock_target_img)

        action = {
            "step": 1,
            "target": "Test Tower",
            "upgrade_path": {"path_1": 1}
        }

        with patch.object(action_manager, '_attempt_upgrade_verification') as mock_verify:
            mock_verify.side_effect = UpgradeVerificationError("Verification failed after retries")

            with pytest.raises(UpgradeVerificationError):
                action_manager.run_upgrade_action(action)

    @patch('btd6_auto.actions.activate_btd6_window')
    def test_cursor_cleanup_on_error(self, mock_activate, action_manager):
        """Test that cursor cleanup happens even when errors occur."""
        action = {
            "target": "Unknown Tower",
            "upgrade_path": {"path_1": 1}
        }

        with patch('btd6_auto.actions.move_and_click') as mock_move_click:
            with patch('btd6_auto.actions.cursor_resting_spot', return_value=(0, 0)):
                # Should raise validation error
                with pytest.raises(UpgradeStateError):
                    action_manager.run_upgrade_action(action)

                # Cursor cleanup should still happen
                mock_move_click.assert_called_once_with(0, 0)

    @patch('btd6_auto.actions.activate_btd6_window')
    @patch('btd6_auto.actions.try_targeting_success')
    def test_debug_tracking_completed_on_error(self, mock_targeting, mock_activate, action_manager):
        """Test that debug tracking is completed even when errors occur."""
        action_manager.monkey_positions = {"Test Tower": (100, 200)}
        mock_target_img = Mock()
        mock_targeting.return_value = (True, "region1", mock_target_img)

        action = {
            "step": 1,
            "target": "Test Tower",
            "upgrade_path": {"path_1": 1}
        }

        with patch.object(action_manager, '_attempt_upgrade_verification') as mock_verify:
            mock_verify.side_effect = UpgradeVerificationError("Verification failed")

            with patch.object(action_manager.debug_manager, 'finish_performance_tracking') as mock_finish:
                with pytest.raises(UpgradeVerificationError):
                    action_manager.run_upgrade_action(action)

                # Debug tracking should be completed (called twice: once for main op, once for verification)
                assert mock_finish.call_count >= 1


class TestUpgradeVerificationHelper:
    """Test the extracted upgrade verification helper method."""

    @pytest.fixture
    def action_manager(self):
        """Create an ActionManager instance for testing."""
        from btd6_auto.currency_reader import CurrencyReader

        map_config = {"map_name": "Test Map", "actions": []}
        global_config = {
            "automation": {
                "timing": {"upgrade_delay": 0.01},
                "retries": {"max_retries": 2, "retry_delay": 0.01}
            }
        }
        currency_reader = Mock(spec=CurrencyReader)
        return ActionManager(map_config, global_config, currency_reader=currency_reader)

    @patch('btd6_auto.actions.keyboard.send')
    @patch('btd6_auto.actions.verify_image_difference')
    @patch('btd6_auto.actions.capture_region')
    def test_verification_success(self, mock_capture, mock_verify_diff, mock_keyboard, action_manager):
        """Test successful upgrade verification."""
        mock_capture.return_value = Mock()
        mock_verify_diff.return_value = (True, 25.0)

        verification_region = Mock()
        targeted_img = Mock()

        result = action_manager._attempt_upgrade_verification(
            "Test Tower", "path_1", 1, "q", verification_region,
            targeted_img, 2, 0.01
        )

        assert result == (True, 25.0)
        assert mock_keyboard.call_count == 1

    @patch('btd6_auto.actions.keyboard.send')
    @patch('btd6_auto.actions.verify_image_difference')
    @patch('btd6_auto.actions.capture_region')
    def test_verification_failure_raises_exception(self, mock_capture, mock_verify_diff,
                                                  mock_keyboard, action_manager):
        """Test that verification failure raises UpgradeVerificationError."""
        mock_capture.return_value = Mock()
        mock_verify_diff.return_value = (False, 5.0)  # Always fails verification

        verification_region = Mock()
        targeted_img = Mock()

        with pytest.raises(UpgradeVerificationError, match="Upgrade verification failed for.*after 2 attempts"):
            action_manager._attempt_upgrade_verification(
                "Test Tower", "path_1", 1, "q", verification_region,
                targeted_img, 2, 0.01
            )

        # Should attempt all retries
        assert mock_keyboard.call_count == 2

    @patch('btd6_auto.actions.keyboard.send')
    @patch('btd6_auto.actions.verify_image_difference')
    @patch('btd6_auto.actions.capture_region')
    def test_verification_retry_logic(self, mock_capture, mock_verify_diff,
                                     mock_keyboard, action_manager):
        """Test that verification properly retries before succeeding."""
        mock_capture.return_value = Mock()
        # Fail first attempt, succeed second
        mock_verify_diff.side_effect = [(False, 5.0), (True, 30.0)]

        verification_region = Mock()
        targeted_img = Mock()

        result = action_manager._attempt_upgrade_verification(
            "Test Tower", "path_1", 1, "q", verification_region,
            targeted_img, 3, 0.01
        )

        assert result == (True, 30.0)
        assert mock_keyboard.call_count == 2