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

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PerformanceMonitor, cls).__new__(cls)
        return cls._instance

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
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"⏱️ Performance metric - {operation_name}: {duration:.4f}s")
                PerformanceMonitor.record_metric(operation_name, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"❌ Error in {operation_name}: {str(e)} (took {duration:.4f}s)")
                raise
        return wrapper
    return decorator

# Singleton instance
performance_monitor = PerformanceMonitor()