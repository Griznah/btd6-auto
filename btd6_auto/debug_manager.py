"""
Debug manager for BTD6 automation bot.

Provides structured logging and debugging capabilities with performance monitoring
and error tracking throughout the application.
"""

import logging
import time
import json
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path
import traceback

class DebugLevel(Enum):
    """Debug logging levels."""
    NONE = 0
    BASIC = 1
    DETAILED = 2
    VERBOSE = 3


class PerformanceTracker:
    """Tracks performance metrics for operations."""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.checkpoints = []

    def start(self) -> None:
        """Start timing an operation."""
        self.start_time = time.time()

    def checkpoint(self, name: str) -> None:
        """Record a checkpoint time."""
        if self.start_time is not None:
            self.checkpoints.append({
                'name': name,
                'time': time.time() - self.start_time
            })

    def finish(self) -> float:
        """Finish timing and return total duration."""
        if self.start_time is None:
            return 0.0
        total_time = time.time() - self.start_time
        self.start_time = None
        return total_time


class DebugManager:
    """
    Centralized debug manager for structured logging and performance monitoring.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize debug manager.

        Args:
            config: Debug configuration dictionary
        """
        self.config = config
        self.enabled = config.get('enabled', False)
        self.level = DebugLevel(config.get('level', DebugLevel.BASIC.value))
        self.log_to_file = config.get('log_to_file', True)
        self.log_to_console = config.get('log_to_console', True)
        self.screenshot_on_error = config.get('screenshot_on_error', True)
        self.performance_tracking = config.get('performance_tracking', True)

        # Setup logging
        self._setup_logging()

        # Performance tracking
        self.performance_data: Dict[str, List[float]] = {}
        self.active_operations: Dict[str, PerformanceTracker] = {}

        # Error tracking
        self.error_history: List[Dict[str, Any]] = []

        # Component-specific loggers
        self.loggers = {}

    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        # Create logs directory if it doesn't exist
        if self.log_to_file:
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)

            # Create filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = log_dir / f'btd6_auto_{timestamp}.log'

            # Setup file handler
            file_handler = logging.FileHandler(log_file)
            # In verbose mode, limit file logging to WARNING level to reduce I/O overhead
            if self.level.value >= 3:
                file_handler.setLevel(logging.WARNING)
            else:
                file_handler.setLevel(logging.DEBUG)

            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)

            # Setup root logger
            root_logger = logging.getLogger('btd6_auto')
            root_logger.setLevel(logging.DEBUG)
            root_logger.addHandler(file_handler)

        # Setup console logging
        if self.log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # Simple formatter for console
            console_formatter = logging.Formatter(
                '%(levelname)s: %(message)s'
            )
            console_handler.setFormatter(console_formatter)

            if not self.log_to_file:
                root_logger = logging.getLogger('btd6_auto')
                root_logger.setLevel(logging.INFO)
                root_logger.addHandler(console_handler)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger for a specific component.

        Args:
            name: Component name (e.g., 'ActionManager', 'VisionManager')

        Returns:
            Logger instance for the component
        """
        if name not in self.loggers:
            self.loggers[name] = logging.getLogger(f'btd6_auto.{name}')
        return self.loggers[name]

    def log_basic(self, component: str, message: str, level: str = 'info') -> None:
        """
        Log basic level information.

        Args:
            component: Component name
            message: Log message
            level: Log level ('debug', 'info', 'warning', 'error')
        """
        if not self.enabled or self.level.value < DebugLevel.BASIC.value:
            return

        logger = self.get_logger(component)
        getattr(logger, level)(message)

    def log_detailed(self, component: str, message: str, **kwargs) -> None:
        """
        Log detailed level information with context.

        Args:
            component: Component name
            message: Log message
            **kwargs: Additional context data
        """
        if not self.enabled or self.level.value < DebugLevel.DETAILED.value:
            return

        # Format message with context
        if kwargs:
            context_str = ' | '.join(f'{k}={v}' for k, v in kwargs.items())
            full_message = f'{message} | {context_str}'
        else:
            full_message = message

        logger = self.get_logger(component)
        logger.info(full_message)

    def log_verbose(self, component: str, message: str, data: Optional[Dict] = None) -> None:
        """
        Log verbose level information with full context.

        Args:
            component: Component name
            message: Log message
            data: Optional data dictionary to include
        """
        if not self.enabled or self.level.value < DebugLevel.VERBOSE.value:
            return

        logger = self.get_logger(component)

        if data:
            # Format data as JSON for readability
            data_str = json.dumps(data, indent=2, default=str)
            full_message = f'{message}\nData: {data_str}'
        else:
            full_message = message

        logger.debug(full_message)

    def start_performance_tracking(self, operation: str) -> Optional[str]:
        """
        Start tracking performance for an operation.

        Args:
            operation: Operation name

        Returns:
            Operation ID if tracking is enabled, None otherwise
        """
        # Disable performance tracking in verbose mode (level 3) to reduce overhead
        if not self.enabled or not self.performance_tracking or self.level.value >= 3:
            return None

        operation_id = f'{operation}_{int(time.time() * 1000)}'
        tracker = PerformanceTracker(operation)
        tracker.start()
        self.active_operations[operation_id] = tracker

        self.log_detailed('Performance', f'Started tracking: {operation}',
                         operation_id=operation_id)

        return operation_id

    def add_checkpoint(self, operation_id: str, checkpoint_name: str) -> None:
        """
        Add a checkpoint to an active operation.

        Args:
            operation_id: Operation ID from start_performance_tracking
            checkpoint_name: Name of the checkpoint
        """
        if not self.enabled or not self.performance_tracking:
            return

        if operation_id in self.active_operations:
            self.active_operations[operation_id].checkpoint(checkpoint_name)
            self.log_verbose('Performance', f'Checkpoint: {checkpoint_name}',
                           {'operation_id': operation_id})

    def finish_performance_tracking(self, operation_id: str) -> Optional[float]:
        """
        Finish tracking performance for an operation.

        Args:
            operation_id: Operation ID from start_performance_tracking

        Returns:
            Total duration in seconds if tracking was enabled, None otherwise
        """
        if not self.enabled or not self.performance_tracking:
            return None

        if operation_id not in self.active_operations:
            return None

        tracker = self.active_operations[operation_id]
        duration = tracker.finish()

        # Store performance data
        operation_name = tracker.operation_name
        if operation_name not in self.performance_data:
            self.performance_data[operation_name] = []
        self.performance_data[operation_name].append(duration)

        # Log performance
        self.log_detailed('Performance',
                         f'Completed: {operation_name} in {duration:.3f}s',
                         operation_id=operation_id,
                         checkpoints=len(tracker.checkpoints))

        if tracker.checkpoints:
            checkpoint_data = {
                'operation': operation_name,
                'total_duration': duration,
                'checkpoints': tracker.checkpoints
            }
            self.log_verbose('Performance', 'Performance breakdown', checkpoint_data)

        # Clean up
        del self.active_operations[operation_id]

        return duration

    def log_error(self, component: str, error: Exception, context: Optional[Dict] = None) -> None:
        """
        Log an error with full context and traceback.

        Args:
            component: Component name
            error: Exception that occurred
            context: Additional context information
        """
        if not self.enabled:
            return

        error_data = {
            'timestamp': datetime.now().isoformat(),
            'component': component,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {}
        }

        # Store in error history
        self.error_history.append(error_data)

        # Keep only last 100 errors
        if len(self.error_history) > 100:
            self.error_history.pop(0)

        # Log the error
        logger = self.get_logger(component)
        logger.error(f'Error in {component}: {error}')
        logger.debug(f'Traceback: {error_data["traceback"]}')

        if context:
            logger.debug(f'Context: {json.dumps(context, indent=2, default=str)}')

        # TODO: Add screenshot functionality if needed
        if self.screenshot_on_error:
            # This would need to be implemented with the vision system
            pass

    def log_vision_result(self, operation: str, success: bool, confidence: Optional[float] = None,
                         match_info: Optional[Dict] = None, processing_time: Optional[float] = None) -> None:
        """
        Log vision system results with structured data.

        Args:
            operation: Vision operation being performed
            success: Whether the operation was successful
            confidence: Confidence score (0-1)
            match_info: Additional match information
            processing_time: Time taken for processing
        """
        if not self.enabled:
            return

        vision_data = {
            'operation': operation,
            'success': success,
            'confidence': confidence,
            'processing_time': processing_time
        }

        if match_info:
            vision_data.update(match_info)

        if success:
            self.log_detailed('Vision', f'Vision success: {operation}', **vision_data)
        else:
            self.log_detailed('Vision', f'Vision failed: {operation}', **vision_data)

    def log_action(self, action_type: str, target: Optional[str] = None,
                  success: bool = True, details: Optional[Dict] = None) -> None:
        """
        Log an action performed by the bot.

        Args:
            action_type: Type of action (e.g., 'place_monkey', 'upgrade', 'use_ability')
            target: Target of the action
            success: Whether the action was successful
            details: Additional action details
        """
        if not self.enabled:
            return

        action_data = {
            'action_type': action_type,
            'target': target,
            'success': success
        }

        if details:
            action_data.update(details)

        status = 'Success' if success else 'Failed'
        self.log_detailed('Action', f'{status}: {action_type}', **action_data)

    def get_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Get performance statistics for all tracked operations.

        Returns:
            Dictionary with performance stats for each operation
        """
        stats = {}

        for operation, times in self.performance_data.items():
            if times:
                stats[operation] = {
                    'count': len(times),
                    'total_time': sum(times),
                    'average_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times)
                }

        return stats

    def log_performance_summary(self) -> None:
        """Log a summary of all performance data."""
        if not self.enabled or not self.performance_tracking:
            return

        stats = self.get_performance_stats()

        if not stats:
            self.log_basic('Performance', 'No performance data available')
            return

        self.log_basic('Performance', 'Performance Summary:')

        for operation, data in stats.items():
            self.log_basic('Performance',
                          f'  {operation}: {data["count"]} operations, '
                          f'avg: {data["average_time"]:.3f}s, '
                          f'total: {data["total_time"]:.3f}s')

    def clear_performance_data(self) -> None:
        """Clear all performance tracking data."""
        self.performance_data.clear()
        self.log_basic('Performance', 'Performance data cleared')