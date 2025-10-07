"""
Async API client module for fetching data from external services.
Handles communication with Frappe API for check-ins and leave applications using aiohttp.
Provides significant performance improvements over the synchronous version.
"""

import json
import aiohttp
import asyncio
import pytz
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from config import API_URL, LEAVE_API_URL, EMPLOYEE_API_URL, get_api_headers
from utils import normalize_leave_type

logger = logging.getLogger(__name__)


@dataclass
class AsyncAPIClientConfig:
    """Configuration for async API client."""
    timeout: int = 30
    max_connections: int = 20
    connection_timeout: int = 10
    page_length: int = 100
    max_retries: int = 3
    retry_delay: float = 1.0


class AsyncAPIClient:
    """Async client for handling API requests to Frappe/ERPNext with connection pooling and retries."""

    def __init__(self, config: Optional[AsyncAPIClientConfig] = None):
        """Initialize async API client with configuration."""
        self.config = config or AsyncAPIClientConfig()
        self.checkin_url = API_URL
        self.leave_url = LEAVE_API_URL
        self.employee_url = EMPLOYEE_API_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers: Optional[Dict[str, str]] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._initialize_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _initialize_session(self) -> None:
        """Initialize aiohttp session with optimized connector and timeout settings."""
        try:
            self.headers = get_api_headers()
        except ValueError as e:
            logger.error(f"Error validando credenciales API: {e}")
            raise

        # Create optimized connector with connection pooling
        connector = aiohttp.TCPConnector(
            limit=self.config.max_connections,
            limit_per_host=self.config.max_connections // 2,
            ttl_dns_cache=300,  # Cache DNS for 5 minutes
            use_dns_cache=True,
            enable_cleanup_closed=True,
            force_close=False,
        )

        # Create timeout configuration
        timeout = aiohttp.ClientTimeout(
            total=self.config.timeout,
            connect=self.config.connection_timeout,
            sock_read=self.config.timeout
        )

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers
        )

        logger.debug(f"Async API client initialized with max_connections={self.config.max_connections}")

    async def close(self) -> None:
        """Close the aiohttp session and cleanup resources."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.debug("Async API client session closed")

    async def _make_request_with_retry(
        self,
        url: str,
        params: Dict[str, Any],
        method: str = 'GET'
    ) -> Dict[str, Any]:
        """
        Make HTTP request with exponential backoff retry logic.

        Args:
            url: Request URL
            params: Query parameters
            method: HTTP method (default: GET)

        Returns:
            JSON response data

        Raises:
            aiohttp.ClientError: If all retries are exhausted
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager or call _initialize_session().")

        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                async with self.session.request(method, url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    logger.debug(f"Request successful on attempt {attempt + 1}")
                    return data

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Request failed after {self.config.max_retries + 1} attempts: {e}")

        raise last_exception

    async def fetch_checkins_paginated(
        self,
        start_date: str,
        end_date: str,
        device_filter: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch all check-in records with optimized concurrent pagination.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            device_filter: Device filter pattern (e.g., "%villas%")

        Returns:
            List of check-in records with normalized timezone
        """
        logger.debug(f"Obteniendo check-ins asíncronos para dispositivo '{device_filter}'...")

        filters = json.dumps([
            ["Employee Checkin", "time", "Between", [start_date, end_date]],
            ["Employee Checkin", "device_id", "like", device_filter],
        ])

        # First, get total count to optimize pagination strategy
        initial_params = {
            "fields": json.dumps(["employee", "employee_name", "time"]),
            "filters": filters,
            "limit_start": 0,
            "limit_page_length": 1,
        }

        try:
            initial_data = await self._make_request_with_retry(self.checkin_url, initial_params)
            total_records = len(initial_data.get("data", []))

            if total_records == 0:
                logger.info("No se encontraron registros de check-in")
                return []

            # Calculate optimal page size based on total records
            optimal_page_size = min(self.config.page_length, max(50, total_records // 10))
            total_pages = (total_records + optimal_page_size - 1) // optimal_page_size

            logger.info(f"Se esperan {total_records} registros, usando {total_pages} páginas de {optimal_page_size} registros")

            # Create tasks for concurrent page fetching
            tasks = []
            for page in range(total_pages):
                limit_start = page * optimal_page_size
                params = {
                    "fields": json.dumps(["employee", "employee_name", "time"]),
                    "filters": filters,
                    "limit_start": limit_start,
                    "limit_page_length": optimal_page_size,
                }
                task = self._fetch_and_process_page(self.checkin_url, params)
                tasks.append(task)

            # Execute all pages concurrently
            page_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and handle any exceptions
            all_records = []
            for i, result in enumerate(page_results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching page {i + 1}: {result}")
                    continue

                page_data = result.get("data", [])
                if page_data:
                    # Normalize timezone for records
                    normalized_records = self._normalize_timezones(page_data)
                    all_records.extend(normalized_records)

            logger.info(f"Se obtuvieron {len(all_records)} registros de la API asíncrona.")
            return all_records

        except Exception as e:
            logger.error(f"Error en fetch_checkins_paginated: {e}")
            return []

    async def _fetch_and_process_page(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch a single page and process the data."""
        data = await self._make_request_with_retry(url, params)
        return data

    def _normalize_timezones(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize timezone from UTC to America/Mexico_City for a list of records."""
        mexico_tz = pytz.timezone("America/Mexico_City")
        normalized_records = []

        for record in records:
            try:
                time_utc = datetime.fromisoformat(record["time"].replace("Z", "+00:00"))
                time_mexico = time_utc.astimezone(mexico_tz)
                record["time"] = time_mexico.isoformat()
                normalized_records.append(record)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error normalizando timezone para registro {record}: {e}")
                normalized_records.append(record)  # Keep original if normalization fails

        return normalized_records

    async def fetch_leave_applications_async(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch all approved leave applications with optimized concurrent requests.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of approved leave application records
        """
        logger.debug(f"Obteniendo solicitudes de permisos asíncronas para período {start_date} - {end_date}...")

        # Construct the optimized URL
        url = f'https://erp.asiatech.com.mx/api/resource/Leave Application?fields=["employee","employee_name","leave_type","from_date","to_date","status","half_day"]&filters=[["status","=","Approved"],["from_date",">=","{start_date}"],["to_date","<=","{end_date}"]]'

        try:
            # First request to get total count
            initial_params = {
                "limit_start": 0,
                "limit_page_length": 1,
            }

            initial_data = await self._make_request_with_retry(url, initial_params)
            total_records = len(initial_data.get("data", []))

            if total_records == 0:
                logger.info("No se encontraron solicitudes de permiso")
                return []

            # For leave applications, use smaller page size as records are typically fewer
            optimal_page_size = min(200, max(50, total_records // 5))
            total_pages = (total_records + optimal_page_size - 1) // optimal_page_size

            logger.info(f"Se esperan {total_records} solicitudes de permiso, usando {total_pages} páginas")

            # Create tasks for concurrent page fetching
            tasks = []
            for page in range(total_pages):
                limit_start = page * optimal_page_size
                params = {
                    "limit_start": limit_start,
                    "limit_page_length": optimal_page_size,
                }
                task = self._fetch_and_process_page(url, params)
                tasks.append(task)

            # Execute all pages concurrently
            page_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            all_leave_records = []
            for i, result in enumerate(page_results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching leave applications page {i + 1}: {result}")
                    continue

                page_data = result.get("data", [])
                all_leave_records.extend(page_data)

            logger.info(f"Se obtuvieron {len(all_leave_records)} solicitudes de permiso aprobadas de API asíncrona.")

            if all_leave_records:
                logger.debug("Ejemplo de solicitudes de permiso recuperadas:")
                for i, leave in enumerate(all_leave_records[:3]):
                    half_day_info = f" (medio día)" if leave.get("half_day") == 1 else ""
                    logger.debug(f"   - {leave['employee_name']}: {leave['leave_type']}{half_day_info} ({leave['from_date']} - {leave['to_date']})")

            return all_leave_records

        except Exception as e:
            logger.error(f"Error en fetch_leave_applications_async: {e}")
            return []

    async def fetch_employee_joining_dates_async(self) -> List[Dict[str, Any]]:
        """
        Fetch all employee records with optimized concurrent requests.

        Returns:
            List of employee records with 'employee' and 'date_of_joining'.
        """
        logger.debug("Obteniendo fechas de contratación de empleados asíncronamente...")

        params = {
            "fields": json.dumps(["employee", "date_of_joining"]),
            "limit_start": 0,
            "limit_page_length": 1,
        }

        try:
            # First request to get total count
            initial_data = await self._make_request_with_retry(self.employee_url, params)
            total_records = len(initial_data.get("data", []))

            if total_records == 0:
                logger.info("No se encontraron registros de empleados")
                return []

            # Optimize page size for employee data
            optimal_page_size = min(500, max(100, total_records // 5))
            total_pages = (total_records + optimal_page_size - 1) // optimal_page_size

            logger.info(f"Se esperan {total_records} registros de empleados, usando {total_pages} páginas")

            # Create tasks for concurrent page fetching
            tasks = []
            for page in range(total_pages):
                limit_start = page * optimal_page_size
                params = {
                    "fields": json.dumps(["employee", "date_of_joining"]),
                    "limit_start": limit_start,
                    "limit_page_length": optimal_page_size,
                }
                task = self._fetch_and_process_page(self.employee_url, params)
                tasks.append(task)

            # Execute all pages concurrently
            page_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            all_records = []
            for i, result in enumerate(page_results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching employee page {i + 1}: {result}")
                    continue

                page_data = result.get("data", [])
                all_records.extend(page_data)

            logger.info(f"Se obtuvieron {len(all_records)} registros de empleados de API asíncrona.")
            return all_records

        except Exception as e:
            logger.error(f"Error en fetch_employee_joining_dates_async: {e}")
            return []


# Convenience function for simple usage
async def fetch_all_data_async(
    start_date: str,
    end_date: str,
    device_filter: str,
    config: Optional[AsyncAPIClientConfig] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Convenience function to fetch all required data asynchronously.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        device_filter: Device filter pattern
        config: Optional configuration for the async client

    Returns:
        Tuple of (checkins, leave_applications, employee_joining_dates)
    """
    async with AsyncAPIClient(config) as client:
        # Execute all three requests concurrently
        tasks = [
            client.fetch_checkins_paginated(start_date, end_date, device_filter),
            client.fetch_leave_applications_async(start_date, end_date),
            client.fetch_employee_joining_dates_async()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions and return results
        checkins = results[0] if not isinstance(results[0], Exception) else []
        leave_applications = results[1] if not isinstance(results[1], Exception) else []
        employee_joining_dates = results[2] if not isinstance(results[2], Exception) else []

        if any(isinstance(result, Exception) for result in results):
            logger.error("Some async requests failed, returning partial results")

        return checkins, leave_applications, employee_joining_dates