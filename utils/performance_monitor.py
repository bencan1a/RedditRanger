import time
import logging
import functools
from typing import Optional, Callable, Any
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class PerformanceMonitor:
    _instance = None
    _metrics = {}
    _start_times = {}  # Track operation start times
    _active_operations = set()  # Prevent duplicate measurements

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PerformanceMonitor, cls).__new__(cls)
        return cls._instance

    @classmethod
    def start_operation(cls, name: str):
        """Mark the start of a performance-tracked operation"""
        if name not in cls._active_operations:
            cls._start_times[name] = time.time()
            cls._active_operations.add(name)
            logger.info(f"⏱️ Starting operation: {name}")

    @classmethod
    def end_operation(cls, name: str):
        """Mark the end of a performance-tracked operation"""
        if name in cls._active_operations:
            if name in cls._start_times:
                duration = time.time() - cls._start_times[name]
                cls.record_metric(name, duration)
            cls._active_operations.remove(name)
            cls._start_times.pop(name, None)

    @classmethod
    def record_metric(cls, name: str, value: float, timestamp: Optional[datetime] = None):
        """Record a performance metric"""
        if timestamp is None:
            timestamp = datetime.now()

        if name not in cls._metrics:
            cls._metrics[name] = []

        cls._metrics[name].append({
            'value': value,
            'timestamp': timestamp
        })

        # Only log if this is a new measurement, not a duplicate
        if name not in cls._active_operations:
            logger.info(f"⏱️ Performance metric - {name}: {value:.4f}s")

    @classmethod
    def get_metrics(cls, name: Optional[str] = None):
        """Retrieve recorded metrics"""
        if name:
            return cls._metrics.get(name, [])
        return cls._metrics

    @classmethod
    def get_latest_metrics(cls):
        """Get the most recent metrics for each category"""
        latest = {}
        for name, measurements in cls._metrics.items():
            if measurements:
                latest[name] = measurements[-1]['value']
        return latest

def timing_decorator(operation_name: str):
    """Decorator to measure execution time of functions"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            monitor = PerformanceMonitor()

            # Only start timing if not already being measured
            if operation_name not in monitor._active_operations:
                monitor.start_operation(operation_name)

                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    logger.error(f"❌ Error in {operation_name}: {str(e)}")
                    raise
                finally:
                    monitor.end_operation(operation_name)
            else:
                return func(*args, **kwargs)

        return wrapper
    return decorator

# Singleton instance
performance_monitor = PerformanceMonitor()