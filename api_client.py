"""
API client module for fetching data from external services.
Handles communication with Frappe API for check-ins and leave applications.
"""

import json
import requests
import pytz
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from config import API_URL, LEAVE_API_URL, EMPLOYEE_API_URL, get_api_headers
from utils import normalize_leave_type

logger = logging.getLogger(__name__)


class APIClient:
    """Client for handling API requests to Frappe/ERPNext."""
    
    def __init__(self):
        """Initialize API client with default configuration."""
        self.checkin_url = API_URL
        self.leave_url = LEAVE_API_URL
        self.employee_url = EMPLOYEE_API_URL
        self.page_length = 100
        self.timeout = 30
    
    def fetch_checkins(self, start_date: str, end_date: str, device_filter: str) -> List[Dict[str, Any]]:
        """
        Fetches all check-in records from the API for a date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format  
            device_filter: Device filter pattern (e.g., "%villas%")
            
        Returns:
            List of check-in records with normalized timezone
        """
        logger.debug(f"Obteniendo check-ins desde API para dispositivo '{device_filter}'...")
        
        try:
            headers = get_api_headers()
        except ValueError as e:
            logger.error(f"Error validando credenciales API: {e}")
            return []
        
        filters = json.dumps([
            ["Employee Checkin", "time", "Between", [start_date, end_date]],
            ["Employee Checkin", "device_id", "like", device_filter],
        ])
        params = {
            "fields": json.dumps(["employee", "employee_name", "time"]),
            "filters": filters,
        }

        all_records = []
        limit_start = 0

        while True:
            params["limit_start"] = limit_start
            params["limit_page_length"] = self.page_length
            
            try:
                response = requests.get(
                    self.checkin_url, 
                    headers=headers, 
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json().get("data", [])
                
                if not data:
                    break

                # Normalize timezone from UTC to America/Mexico_City
                for record in data:
                    time_utc = datetime.fromisoformat(record["time"].replace("Z", "+00:00"))
                    mexico_tz = pytz.timezone("America/Mexico_City")
                    time_mexico = time_utc.astimezone(mexico_tz)
                    record["time"] = time_mexico.isoformat()

                all_records.extend(data)
                
                if len(data) < self.page_length:
                    break
                    
                limit_start += self.page_length
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error llamando API: {e}")
                return []

        logger.info(f"Se obtuvieron {len(all_records)} registros de la API.")
        return all_records

    def fetch_leave_applications(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Fetches all approved leave applications from the API for a date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of approved leave application records
        """
        logger.debug(f"Obteniendo solicitudes de permisos aprobadas de API para período {start_date} - {end_date}...")
        
        try:
            headers = get_api_headers()
        except ValueError as e:
            logger.error(f"Error validando credenciales API: {e}")
            return []
        url = f'https://erp.asiatech.com.mx/api/resource/Leave Application?fields=["employee","employee_name","leave_type","from_date","to_date","status","half_day"]&filters=[["status","=","Approved"],["from_date",">=","{start_date}"],["to_date","<=","{end_date}"]]'

        all_leave_records = []
        limit_start = 0

        while True:
            params = {
                "limit_start": limit_start,
                "limit_page_length": self.page_length,
            }

            try:
                response = requests.get(
                    url, 
                    headers=headers, 
                    params=params, 
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json().get("data", [])

                if not data:
                    break

                all_leave_records.extend(data)

                if len(data) < self.page_length:
                    break

                limit_start += self.page_length

            except requests.exceptions.Timeout:
                logger.warning("Timeout obteniendo solicitudes de permisos. Reintentando...")
                continue
            except requests.exceptions.RequestException as e:
                logger.error(f"Error obteniendo solicitudes de permisos de API: {e}")
                return []

        logger.info(f"Se obtuvieron {len(all_leave_records)} solicitudes de permiso aprobadas de API.")

        if all_leave_records:
            logger.debug("Ejemplo de solicitudes de permiso recuperadas:")
            for i, leave in enumerate(all_leave_records[:3]):
                half_day_info = f" (medio día)" if leave.get("half_day") == 1 else ""
                logger.debug(f"   - {leave['employee_name']}: {leave['leave_type']}{half_day_info} ({leave['from_date']} - {leave['to_date']})")

        return all_leave_records

    def fetch_employee_joining_dates(self) -> List[Dict[str, Any]]:
        """
        Fetches all employee records from the API to get their joining dates.

        Returns:
            List of employee records with 'employee' and 'date_of_joining'.
        """
        logger.debug("Obteniendo todas las fechas de contratación de empleados de API...")

        try:
            headers = get_api_headers()
        except ValueError as e:
            logger.error(f"Error validando credenciales API: {e}")
            return []

        params = {
            "fields": json.dumps(["employee", "date_of_joining"]),
        }

        all_records = []
        limit_start = 0

        while True:
            params["limit_start"] = limit_start
            params["limit_page_length"] = self.page_length

            try:
                response = requests.get(
                    self.employee_url,
                    headers=headers,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json().get("data", [])

                if not data:
                    break

                all_records.extend(data)

                if len(data) < self.page_length:
                    break

                limit_start += self.page_length

            except requests.exceptions.RequestException as e:
                logger.error(f"Error llamando API de Empleados: {e}")
                return []

        logger.info(f"Se obtuvieron {len(all_records)} registros de empleados de API.")
        return all_records


def procesar_permisos_empleados(leave_data: List[Dict[str, Any]]) -> Dict[str, Dict]:
    """
    Processes leave data and creates a dictionary organized by employee and date.
    Properly handles half-day leaves.
    
    Args:
        leave_data: List of leave application records from API
        
    Returns:
        Dictionary organized by employee code and date with leave information
    """
    if not leave_data:
        return {}

    logger.debug("Procesando solicitudes de permiso por empleado y fecha...")

    permisos_por_empleado = {}
    total_dias_permiso = 0
    permisos_medio_dia = 0

    for permiso in leave_data:
        employee_code = permiso["employee"]
        from_date = datetime.strptime(permiso["from_date"], "%Y-%m-%d").date()
        to_date = datetime.strptime(permiso["to_date"], "%Y-%m-%d").date()
        is_half_day = permiso.get("half_day") == 1

        if employee_code not in permisos_por_empleado:
            permisos_por_empleado[employee_code] = {}

        # If it's a half-day leave, only process the specific date
        if is_half_day:
            leave_type_normalized = normalize_leave_type(permiso["leave_type"])

            permisos_por_empleado[employee_code][from_date] = {
                "leave_type": permiso["leave_type"],
                "leave_type_normalized": leave_type_normalized,
                "employee_name": permiso["employee_name"],
                "from_date": from_date,
                "to_date": to_date,
                "status": permiso["status"],
                "is_half_day": True,
                "dias_permiso": 0.5,  # Half day
            }
            total_dias_permiso += 0.5
            permisos_medio_dia += 1
        else:
            # Full day leave - process the entire date range
            current_date = from_date
            while current_date <= to_date:
                leave_type_normalized = normalize_leave_type(permiso["leave_type"])

                permisos_por_empleado[employee_code][current_date] = {
                    "leave_type": permiso["leave_type"],
                    "leave_type_normalized": leave_type_normalized,
                    "employee_name": permiso["employee_name"],
                    "from_date": from_date,
                    "to_date": to_date,
                    "status": permiso["status"],
                    "is_half_day": False,
                    "dias_permiso": 1.0,  # Full day
                }
                current_date += timedelta(days=1)
                total_dias_permiso += 1.0

    logger.info(f"Se procesaron solicitudes de permiso para {len(permisos_por_empleado)} empleados, "
          f"{total_dias_permiso:.1f} días totales de permiso ({permisos_medio_dia} de medio día).")

    return permisos_por_empleado