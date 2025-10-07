"""
Comprehensive tests for performance enhancement features.
Tests connection pooling, caching, async patterns, structured logging, and performance monitoring.
"""

import pytest
import asyncio
import time
import json
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

# Import modules to test
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_postgres_connection import (
    get_connection_pool,
    get_connection_from_pool,
    return_connection_to_pool,
    obtener_horario_empleado_cached,
    clear_horario_cache,
    get_cache_stats,
    connection_context_manager
)
from async_api_client import AsyncAPIClient, AsyncAPIClientConfig, fetch_all_data_async
from structured_logger import StructuredLogger, LogLevel, get_logger, configure_logging
from performance_monitor import PerformanceMonitor, get_performance_monitor, monitor_performance


class TestConnectionPooling:
    """Test database connection pooling functionality."""

    @pytest.fixture
    def mock_db_config(self):
        """Mock database configuration for testing."""
        with patch.dict(os.environ, {
            'DB_HOST': 'localhost',
            'DB_NAME': 'test_db',
            'DB_USER': 'test_user',
            'DB_PASSWORD': 'test_password',
            'MIN_POOL_CONNECTIONS': '2',
            'MAX_POOL_CONNECTIONS': '5'
        }):
            yield

    @patch('db_postgres_connection.pool.ThreadedConnectionPool')
    def test_get_connection_pool_initialization(self, mock_pool_class, mock_db_config):
        """Test connection pool initialization."""
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool

        # First call should create pool
        pool = get_connection_pool()
        assert pool is not None
        mock_pool_class.assert_called_once()

        # Second call should return existing pool
        pool2 = get_connection_pool()
        assert pool is pool2
        mock_pool_class.assert_called_once()  # Still only called once

    @patch('db_postgres_connection.get_connection_pool')
    def test_get_connection_from_pool(self, mock_get_pool, mock_db_config):
        """Test getting connection from pool."""
        mock_pool = Mock()
        mock_conn = Mock()
        mock_pool.getconn.return_value = mock_conn
        mock_get_pool.return_value = mock_pool

        conn = get_connection_from_pool()
        assert conn is mock_conn
        mock_pool.getconn.assert_called_once()

    @patch('db_postgres_connection.get_connection_pool')
    def test_return_connection_to_pool(self, mock_get_pool, mock_db_config):
        """Test returning connection to pool."""
        mock_pool = Mock()
        mock_get_pool.return_value = mock_pool
        mock_conn = Mock()

        return_connection_to_pool(mock_conn)
        mock_pool.putconn.assert_called_once_with(mock_conn)

    @patch('db_postgres_connection.get_connection_from_pool')
    @patch('db_postgres_connection.return_connection_to_pool')
    def test_connection_context_manager(self, mock_return, mock_get, mock_db_config):
        """Test connection context manager."""
        mock_conn = Mock()
        mock_get.return_value = mock_conn

        with connection_context_manager() as conn:
            assert conn is mock_conn
            mock_get.assert_called_once()

        mock_return.assert_called_once_with(mock_conn)


class TestCaching:
    """Test caching functionality."""

    def test_obtener_horario_empleado_cached(self):
        """Test cached employee schedule lookup."""
        # Clear cache first
        clear_horario_cache()

        # Create test cache data
        cache_horarios = {
            '123': {
                True: {  # Primera quincena
                    1: {'hora_entrada': '08:00', 'hora_salida': '17:00'},
                    2: {'hora_entrada': '08:00', 'hora_salida': '17:00'}
                },
                False: {  # Segunda quincena
                    1: {'hora_entrada': '09:00', 'hora_salida': '18:00'}
                }
            }
        }

        # First call should hit main cache
        result1 = obtener_horario_empleado_cached('123', 1, True, 1)
        expected = {'hora_entrada': '08:00', 'hora_salida': '17:00'}
        assert result1 == (expected, True)

        # Second call with same parameters should hit LRU cache
        result2 = obtener_horario_empleado_cached('123', 1, True, 1)
        assert result2 == (expected, True)

        # Different parameters should not hit cache
        result3 = obtener_horario_empleado_cached('123', 2, True, 1)
        expected2 = {'hora_entrada': '08:00', 'hora_salida': '17:00'}
        assert result3 == (expected2, True)

    def test_cache_stats(self):
        """Test cache statistics functionality."""
        clear_horario_cache()

        cache_horarios = {
            '123': {
                True: {
                    1: {'hora_entrada': '08:00', 'hora_salida': '17:00'}
                }
            }
        }

        # Make some cached calls
        obtener_horario_empleado_cached('123', 1, True, 1)
        obtener_horario_empleado_cached('123', 1, True, 1)  # Cache hit

        stats = get_cache_stats()
        assert 'lru_cache' in stats
        assert 'local_cache_size' in stats
        assert stats['lru_cache']['hits'] >= 1


class TestAsyncAPIClient:
    """Test async API client functionality."""

    @pytest.fixture
    async def async_client(self):
        """Create async client for testing."""
        config = AsyncAPIClientConfig(
            timeout=5,
            max_connections=5,
            page_length=10
        )
        async with AsyncAPIClient(config) as client:
            yield client

    @pytest.mark.asyncio
    async def test_async_client_initialization(self):
        """Test async client initialization."""
        config = AsyncAPIClientConfig(timeout=10, max_connections=20)
        client = AsyncAPIClient(config)

        await client._initialize_session()
        assert client.session is not None
        assert client.headers is not None

        await client.close()

    @pytest.mark.asyncio
    @patch('async_api_client.get_api_headers')
    async def test_async_client_context_manager(self, mock_get_headers):
        """Test async client context manager."""
        mock_get_headers.return_value = {'Authorization': 'Bearer token'}

        async with AsyncAPIClient() as client:
            assert client.session is not None
            assert client.headers is not None
            mock_get_headers.assert_called_once()

    @pytest.mark.asyncio
    @patch('async_api_client.get_api_headers')
    async def test_make_request_with_retry(self, mock_get_headers):
        """Test request with retry logic."""
        mock_get_headers.return_value = {'Authorization': 'Bearer token'}

        config = AsyncAPIClientConfig(max_retries=2, retry_delay=0.1)
        client = AsyncAPIClient(config)
        await client._initialize_session()

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.json.return_value = {'data': [{'id': 1}]}
        mock_response.raise_for_status = Mock()

        with patch.object(client.session, 'request') as mock_request:
            mock_request.return_value.__aenter__.return_value = mock_response

            result = await client._make_request_with_retry('http://test.com', {'param': 'value'})
            assert result == {'data': [{'id': 1}]}

        await client.close()

    @pytest.mark.asyncio
    @patch('async_api_client.get_api_headers')
    async def test_fetch_checkins_paginated(self, mock_get_headers):
        """Test paginated check-in fetching."""
        mock_get_headers.return_value = {'Authorization': 'Bearer token'}

        config = AsyncAPIClientConfig(page_length=5)
        client = AsyncAPIClient(config)
        await client._initialize_session()

        # Mock response with total count
        mock_initial_response = AsyncMock()
        mock_initial_response.json.return_value = {'data': [{'id': i} for i in range(10)]}
        mock_initial_response.raise_for_status = Mock()

        with patch.object(client, '_make_request_with_retry') as mock_request:
            mock_request.return_value = mock_initial_response

            result = await client.fetch_checkins_paginated(
                '2024-01-01', '2024-01-31', '%test%'
            )

            assert len(result) == 10
            mock_request.assert_called()

        await client.close()


class TestStructuredLogger:
    """Test structured logging functionality."""

    def test_structured_logger_initialization(self):
        """Test structured logger initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'test.log')
            logger = StructuredLogger(
                name='test_logger',
                level=LogLevel.DEBUG,
                log_file=log_file,
                enable_console=False,
                enable_json=True
            )

            assert logger.logger.name == 'test_logger'
            assert logger.logger.level == LogLevel.DEBUG.value
            assert len(logger.logger.handlers) == 1  # File handler only

            logger.info('Test message')
            assert os.path.exists(log_file)

            # Check log file content
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert 'Test message' in log_content
                assert 'test_logger' in log_content

    def test_performance_tracker(self):
        """Test performance tracking context manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'test.log')
            logger = StructuredLogger(
                name='test_logger',
                log_file=log_file,
                enable_console=False
            )

            with logger.performance('test_operation', param1='value1'):
                time.sleep(0.01)  # Small delay to measure

            # Check that performance metrics were logged
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert 'Starting test_operation' in log_content
                assert 'Completed test_operation' in log_content
                assert 'duration_seconds' in log_content

    def test_metric_logging(self):
        """Test metric logging functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'test.log')
            logger = StructuredLogger(
                name='test_logger',
                log_file=log_file,
                enable_console=False
            )

            logger.log_metric('test_metric', 42.5, 'ms', operation='test_op')

            with open(log_file, 'r') as f:
                log_content = f.read()
                assert 'test_metric' in log_content
                assert '42.5' in log_content
                assert 'ms' in log_content

    def test_correlation_id(self):
        """Test correlation ID functionality."""
        logger = StructuredLogger(
            name='test_logger',
            enable_console=False,
            enable_json=False  # Disable file output for this test
        )

        # Test custom correlation ID
        custom_id = 'test-corr-123'
        logger.set_correlation_id(custom_id)
        assert logger.get_correlation_id() == custom_id

        # Test auto-generated correlation ID
        logger2 = StructuredLogger(name='test_logger2', enable_console=False, enable_json=False)
        assert len(logger2.get_correlation_id()) == 8  # Should be 8 characters


class TestPerformanceMonitor:
    """Test performance monitoring functionality."""

    def test_performance_monitor_initialization(self):
        """Test performance monitor initialization."""
        monitor = PerformanceMonitor(max_history_size=100, monitoring_interval=0.1)

        assert monitor.max_history_size == 100
        assert monitor.monitoring_interval == 0.1
        assert not monitor._monitoring

    def test_metric_recording(self):
        """Test metric recording functionality."""
        monitor = PerformanceMonitor()

        monitor.record_metric('test_metric', 1.5, 'seconds', operation='test_op')
        monitor.record_metric('test_metric', 2.0, 'seconds', operation='test_op')

        stats = monitor.get_operation_stats('test_op')
        assert stats['count'] == 2
        assert stats['avg_time'] == 1.75
        assert stats['min_time'] == 1.5
        assert stats['max_time'] == 2.0

    def test_database_metrics(self):
        """Test database metric recording."""
        monitor = PerformanceMonitor()

        monitor.record_database_metric('SELECT', 'employees', 50.5, rows_affected=10, cache_hit=True)
        monitor.record_database_metric('INSERT', 'attendance', 25.0, rows_affected=5)

        stats = monitor.get_database_stats()
        assert stats['total_queries'] == 2
        assert stats['cache_hits'] == 1
        assert stats['cache_misses'] == 0
        assert stats['cache_hit_ratio'] == 1.0

    def test_counter_functionality(self):
        """Test counter functionality."""
        monitor = PerformanceMonitor()

        monitor.increment_counter('test_counter', 5)
        monitor.increment_counter('test_counter', 3)

        with monitor._lock:
            assert monitor._counters['test_counter'] == 8.0

    def test_timer_functionality(self):
        """Test timer functionality."""
        monitor = PerformanceMonitor()

        monitor.start_timer('test_timer')
        time.sleep(0.01)  # Small delay
        elapsed = monitor.end_timer('test_timer')

        assert elapsed is not None
        assert elapsed >= 0.01

        # Test ending non-existent timer
        elapsed_none = monitor.end_timer('non_existent')
        assert elapsed_none is None

    def test_performance_report(self):
        """Test performance report generation."""
        monitor = PerformanceMonitor()

        # Add some test data
        monitor.record_metric('test_op', 1.0, 'seconds', operation='test_operation')
        monitor.record_database_metric('SELECT', 'test_table', 25.0)
        monitor.increment_counter('test_counter', 10)

        report = monitor.generate_report()

        assert 'timestamp' in report
        assert 'memory_stats' in report
        assert 'database_stats' in report
        assert 'counters' in report
        assert report['counters']['test_counter'] == 10.0

    def test_performance_decorator(self):
        """Test performance decorator functionality."""
        monitor = PerformanceMonitor()

        @monitor.performance_decorator('test_function')
        def test_function(x):
            time.sleep(0.01)
            return x * 2

        result = test_function(5)
        assert result == 10

        # Check that metric was recorded
        stats = monitor.get_operation_stats('test_function')
        assert stats['count'] == 1
        assert stats['success'] == True

    @patch('psutil.Process')
    def test_memory_monitoring(self, mock_process_class):
        """Test memory monitoring functionality."""
        # Mock psutil Process
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100 MB
        mock_memory_info.vms = 200 * 1024 * 1024  # 200 MB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.memory_percent.return_value = 25.5
        mock_process_class.return_value = mock_process

        with patch('psutil.virtual_memory') as mock_virtual_memory:
            mock_virtual_memory.return_value.available = 400 * 1024 * 1024  # 400 MB
            with patch('gc.get_objects', return_value=[1, 2, 3, 4, 5]):
                monitor = PerformanceMonitor()
                monitor._collect_memory_snapshot()

                assert len(monitor.memory_snapshots) == 1
                snapshot = monitor.memory_snapshots[0]
                assert snapshot.rss_mb == 100.0
                assert snapshot.vms_mb == 200.0
                assert snapshot.percent == 25.5
                assert snapshot.available_mb == 400.0
                assert snapshot.gc_objects == 5

    def test_global_performance_monitor(self):
        """Test global performance monitor functions."""
        # Test getting global monitor
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        assert monitor1 is monitor2

        # Test decorator function
        @monitor_performance('global_test')
        def global_test_func():
            return "test_result"

        result = global_test_func()
        assert result == "test_result"


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for performance enhancements."""

    async def test_async_api_with_monitoring(self):
        """Test async API client with performance monitoring."""
        monitor = PerformanceMonitor()

        with patch('async_api_client.get_api_headers') as mock_headers:
            mock_headers.return_value = {'Authorization': 'Bearer token'}

            config = AsyncAPIClientConfig(timeout=5, page_length=10)
            client = AsyncAPIClient(config)

            with patch.object(client, '_make_request_with_retry') as mock_request:
                mock_response = AsyncMock()
                mock_response.json.return_value = {'data': []}
                mock_response.raise_for_status = Mock()
                mock_request.return_value = mock_response

                await client._initialize_session()

                # Monitor API call performance
                start_time = time.time()
                result = await client.fetch_checkins_paginated('2024-01-01', '2024-01-31', '%test%')
                duration = time.time() - start_time

                assert result == []

                await client.close()

            # Verify metrics were recorded
            db_stats = monitor.get_database_stats()
            # Should have recorded some database-like metrics


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])