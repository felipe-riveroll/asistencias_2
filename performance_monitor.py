"""
Performance monitoring and metrics collection module.
Provides comprehensive performance tracking, memory monitoring, and metrics reporting.
"""

import time
import psutil
import gc
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import json
from pathlib import Path

from structured_logger import get_logger, LogLevel

logger = get_logger('performance_monitor')


@dataclass
class PerformanceMetric:
    """Individual performance metric data structure."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    operation: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class MemorySnapshot:
    """Memory usage snapshot."""
    timestamp: datetime
    rss_mb: float  # Resident Set Size in MB
    vms_mb: float  # Virtual Memory Size in MB
    percent: float  # Memory usage percentage
    available_mb: float  # Available memory in MB
    gc_objects: int  # Number of garbage collector objects


@dataclass
class DatabaseMetric:
    """Database performance metric."""
    timestamp: datetime
    query_type: str
    table: str
    duration_ms: float
    rows_affected: Optional[int] = None
    cache_hit: Optional[bool] = None


class PerformanceMonitor:
    """Main performance monitoring class."""

    def __init__(self, max_history_size: int = 1000, monitoring_interval: float = 1.0):
        """
        Initialize performance monitor.

        Args:
            max_history_size: Maximum number of metrics to keep in history
            monitoring_interval: Interval in seconds for background monitoring
        """
        self.max_history_size = max_history_size
        self.monitoring_interval = monitoring_interval

        # Metrics storage
        self.metrics_history: deque = deque(maxlen=max_history_size)
        self.memory_snapshots: deque = deque(maxlen=max_history_size)
        self.db_metrics: deque = deque(maxlen=max_history_size)

        # Aggregated statistics
        self.operation_stats: Dict[str, List[float]] = defaultdict(list)
        self.operation_counts: Dict[str, int] = defaultdict(int)

        # Monitoring state
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # Performance counters
        self._counters: Dict[str, float] = defaultdict(float)
        self._timers: Dict[str, float] = {}

    def start_monitoring(self) -> None:
        """Start background performance monitoring."""
        if self._monitoring:
            logger.warning("Performance monitoring already started")
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Performance monitoring started")

    def stop_monitoring(self) -> None:
        """Stop background performance monitoring."""
        if not self._monitoring:
            return

        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring:
            try:
                self._collect_memory_snapshot()
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

    def _collect_memory_snapshot(self) -> None:
        """Collect current memory usage snapshot."""
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()

            snapshot = MemorySnapshot(
                timestamp=datetime.now(),
                rss_mb=memory_info.rss / 1024 / 1024,
                vms_mb=memory_info.vms / 1024 / 1024,
                percent=memory_percent,
                available_mb=psutil.virtual_memory().available / 1024 / 1024,
                gc_objects=len(gc.get_objects())
            )

            with self._lock:
                self.memory_snapshots.append(snapshot)

        except Exception as e:
            logger.error(f"Error collecting memory snapshot: {e}")

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str,
        operation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a performance metric.

        Args:
            name: Metric name
            value: Metric value
            unit: Unit of measurement
            operation: Related operation name
            context: Additional context information
        """
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            operation=operation,
            context=context or {}
        )

        with self._lock:
            self.metrics_history.append(metric)

            # Update aggregated statistics
            if operation:
                self.operation_stats[operation].append(value)
                self.operation_counts[operation] += 1

        logger.debug(f"Metric recorded: {name}={value}{unit}", extra={
            'metric_name': name,
            'metric_value': value,
            'metric_unit': unit,
            'operation': operation
        })

    def record_database_metric(
        self,
        query_type: str,
        table: str,
        duration_ms: float,
        rows_affected: Optional[int] = None,
        cache_hit: Optional[bool] = None
    ) -> None:
        """
        Record a database performance metric.

        Args:
            query_type: Type of query (SELECT, INSERT, UPDATE, etc.)
            table: Table name
            duration_ms: Query duration in milliseconds
            rows_affected: Number of rows affected
            cache_hit: Whether the query hit the cache
        """
        metric = DatabaseMetric(
            timestamp=datetime.now(),
            query_type=query_type,
            table=table,
            duration_ms=duration_ms,
            rows_affected=rows_affected,
            cache_hit=cache_hit
        )

        with self._lock:
            self.db_metrics.append(metric)

        logger.debug(f"DB metric recorded: {query_type} {table} ({duration_ms}ms)", extra={
            'db_query_type': query_type,
            'db_table': table,
            'db_duration_ms': duration_ms,
            'db_rows_affected': rows_affected
        })

    def increment_counter(self, name: str, value: float = 1.0) -> None:
        """
        Increment a performance counter.

        Args:
            name: Counter name
            value: Value to add (default: 1.0)
        """
        with self._lock:
            self._counters[name] += value

    def start_timer(self, name: str) -> None:
        """Start a named timer."""
        with self._lock:
            self._timers[name] = time.time()

    def end_timer(self, name: str) -> Optional[float]:
        """
        End a named timer and return elapsed time.

        Args:
            name: Timer name

        Returns:
            Elapsed time in seconds, or None if timer not found
        """
        with self._lock:
            if name not in self._timers:
                return None

            elapsed = time.time() - self._timers[name]
            del self._timers[name]
            return elapsed

    def get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """
        Get statistics for a specific operation.

        Args:
            operation: Operation name

        Returns:
            Dictionary with operation statistics
        """
        with self._lock:
            if operation not in self.operation_stats:
                return {}

            values = self.operation_stats[operation]
            if not values:
                return {}

            return {
                'operation': operation,
                'count': len(values),
                'total_time': sum(values),
                'avg_time': sum(values) / len(values),
                'min_time': min(values),
                'max_time': max(values),
                'last_time': values[-1] if values else None
            }

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get current memory statistics.

        Returns:
            Dictionary with memory statistics
        """
        with self._lock:
            if not self.memory_snapshots:
                return {}

            latest = self.memory_snapshots[-1]
            all_rss = [s.rss_mb for s in self.memory_snapshots]
            all_percent = [s.percent for s in self.memory_snapshots]

            return {
                'current_rss_mb': latest.rss_mb,
                'current_vms_mb': latest.vms_mb,
                'current_percent': latest.percent,
                'available_mb': latest.available_mb,
                'gc_objects': latest.gc_objects,
                'peak_rss_mb': max(all_rss) if all_rss else 0,
                'avg_rss_mb': sum(all_rss) / len(all_rss) if all_rss else 0,
                'peak_percent': max(all_percent) if all_percent else 0,
                'avg_percent': sum(all_percent) / len(all_percent) if all_percent else 0,
                'snapshots_count': len(self.memory_snapshots)
            }

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database performance statistics.

        Returns:
            Dictionary with database statistics
        """
        with self._lock:
            if not self.db_metrics:
                return {}

            # Group by query type
            query_stats = defaultdict(list)
            table_stats = defaultdict(list)
            cache_hits = 0
            cache_misses = 0

            for metric in self.db_metrics:
                query_stats[metric.query_type].append(metric.duration_ms)
                table_stats[metric.table].append(metric.duration_ms)
                if metric.cache_hit is not None:
                    if metric.cache_hit:
                        cache_hits += 1
                    else:
                        cache_misses += 1

            # Calculate statistics
            result = {
                'total_queries': len(self.db_metrics),
                'cache_hits': cache_hits,
                'cache_misses': cache_misses,
                'cache_hit_ratio': cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
            }

            # Query type statistics
            for query_type, durations in query_stats.items():
                result[f'{query_type.lower()}_queries'] = len(durations)
                result[f'{query_type.lower()}_avg_ms'] = sum(durations) / len(durations) if durations else 0
                result[f'{query_type.lower()}_total_ms'] = sum(durations)

            # Table statistics
            table_performance = {}
            for table, durations in table_stats.items():
                table_performance[table] = {
                    'count': len(durations),
                    'avg_ms': sum(durations) / len(durations) if durations else 0,
                    'total_ms': sum(durations)
                }

            result['table_performance'] = table_performance
            return result

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.

        Returns:
            Dictionary with complete performance report
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'monitoring_duration_seconds': len(self.memory_snapshots) * self.monitoring_interval,
            'memory_stats': self.get_memory_stats(),
            'database_stats': self.get_database_stats(),
            'counters': dict(self._counters),
            'active_timers': list(self._timers.keys())
        }

        # Add operation statistics
        operation_summary = {}
        for operation in self.operation_counts:
            operation_summary[operation] = self.get_operation_stats(operation)
        report['operation_summary'] = operation_summary

        return report

    def save_report(self, filepath: str) -> None:
        """
        Save performance report to file.

        Args:
            filepath: Path to save the report
        """
        try:
            report = self.generate_report()
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Performance report saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving performance report: {e}")

    def reset_metrics(self) -> None:
        """Reset all collected metrics."""
        with self._lock:
            self.metrics_history.clear()
            self.memory_snapshots.clear()
            self.db_metrics.clear()
            self.operation_stats.clear()
            self.operation_counts.clear()
            self._counters.clear()
            self._timers.clear()
        logger.info("Performance metrics reset")

    def performance_decorator(self, operation_name: Optional[str] = None):
        """
        Decorator for automatic function performance monitoring.

        Args:
            operation_name: Custom operation name (defaults to function name)
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                start_time = time.time()

                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    self.record_metric(
                        name=f"{func.__name__}_duration",
                        value=duration,
                        unit="seconds",
                        operation=op_name,
                        context={'function': func.__name__, 'success': True}
                    )
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self.record_metric(
                        name=f"{func.__name__}_duration",
                        value=duration,
                        unit="seconds",
                        operation=op_name,
                        context={'function': func.__name__, 'success': False, 'error': str(e)}
                    )
                    raise

            return wrapper
        return decorator


# Global performance monitor instance
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create the global performance monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def start_performance_monitoring() -> None:
    """Start the global performance monitor."""
    monitor = get_performance_monitor()
    monitor.start_monitoring()


def stop_performance_monitoring() -> None:
    """Stop the global performance monitor."""
    monitor = get_performance_monitor()
    monitor.stop_monitoring()


def save_performance_report(filepath: str = None) -> None:
    """
    Save performance report to file.

    Args:
        filepath: Optional filepath (default: logs/performance_report.json)
    """
    if filepath is None:
        filepath = f"logs/performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    monitor = get_performance_monitor()
    monitor.save_report(filepath)


def monitor_performance(operation_name: Optional[str] = None):
    """
    Decorator for performance monitoring using the global monitor.

    Args:
        operation_name: Custom operation name
    """
    return get_performance_monitor().performance_decorator(operation_name)