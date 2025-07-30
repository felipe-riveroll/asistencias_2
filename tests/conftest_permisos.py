"""
Configuración y fixtures para las pruebas de integración de permisos.
"""

import pytest
import pandas as pd
from datetime import date
from unittest.mock import Mock
import sys
import os

# Añadir el directorio raíz al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_leave_data():
    """Datos de muestra para permisos de la API"""
    return [
        {
            "employee": "25",
            "employee_name": "Karla Ivette Chimal Moreno",
            "leave_type": "Incapacidad por enfermedad",
            "from_date": "2025-07-04",
            "to_date": "2025-07-04",
            "status": "Approved",
        },
        {
            "employee": "50",
            "employee_name": "Christian Joel Popoca Domínguez",
            "leave_type": "Vacaciones (después de 6-10 años)",
            "from_date": "2025-07-06",
            "to_date": "2025-07-06",
            "status": "Approved",
        },
        {
            "employee": "47",
            "employee_name": "Maria Brenda Bautista Zavala",
            "leave_type": "Vacaciones (después de 4 años)",
            "from_date": "2025-07-11",
            "to_date": "2025-07-14",
            "status": "Approved",
        },
        {
            "employee": "51",
            "employee_name": "María Fabiola Monfil García",
            "leave_type": "Vacaciones (después de 6-10 años)",
            "from_date": "2025-07-11",
            "to_date": "2025-07-16",
            "status": "Approved",
        },
    ]


@pytest.fixture
def sample_attendance_dataframe():
    """DataFrame de muestra para datos de asistencia"""
    return pd.DataFrame(
        {
            "employee": ["25", "25", "25", "50", "50", "50", "47", "47", "47", "47"],
            "dia": [
                date(2025, 7, 4),  # Permiso
                date(2025, 7, 5),  # Sin permiso
                date(2025, 7, 6),  # Sin permiso
                date(2025, 7, 6),  # Permiso
                date(2025, 7, 7),  # Sin permiso
                date(2025, 7, 8),  # Sin permiso
                date(2025, 7, 11),  # Permiso (inicio rango)
                date(2025, 7, 12),  # Permiso (medio rango)
                date(2025, 7, 13),  # Permiso (medio rango)
                date(2025, 7, 14),  # Permiso (fin rango)
            ],
            "horas_esperadas": ["8:00:00"] * 10,
            "tipo_retardo": [
                "Falta",
                "A Tiempo",
                "A Tiempo",
                "Falta",
                "A Tiempo",
                "Retardo",
                "Falta",
                "Falta",
                "A Tiempo",
                "Falta",
            ],
            "es_falta": [1, 0, 0, 1, 0, 0, 1, 1, 0, 1],
        }
    )


@pytest.fixture
def sample_cache_horarios():
    """Caché de horarios de muestra"""
    return {
        "25": {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None},
        "50": {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None},
        "47": {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None},
        "51": {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None},
    }


@pytest.fixture
def mock_api_response_success():
    """Mock para respuesta exitosa de la API"""
    mock_response = Mock()
    mock_response.json.return_value = {
        "data": [
            {
                "employee": "1",
                "employee_name": "Test Employee",
                "leave_type": "Vacaciones",
                "from_date": "2025-07-16",
                "to_date": "2025-07-16",
                "status": "Approved",
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    return mock_response


@pytest.fixture
def mock_api_response_empty():
    """Mock para respuesta vacía de la API"""
    mock_response = Mock()
    mock_response.json.return_value = {"data": []}
    mock_response.raise_for_status.return_value = None
    return mock_response


@pytest.fixture
def weekend_leave_data():
    """Datos de permiso que incluye fin de semana"""
    return [
        {
            "employee": "65",
            "employee_name": "Marisol Rivera Martínez",
            "leave_type": "Vacaciones (después de 2 años)",
            "from_date": "2025-07-12",  # Viernes
            "to_date": "2025-07-15",  # Lunes (incluye sábado y domingo)
            "status": "Approved",
        }
    ]


@pytest.fixture
def multiple_leaves_same_employee():
    """Múltiples permisos para el mismo empleado"""
    return [
        {
            "employee": "47",
            "employee_name": "Maria Brenda Bautista Zavala",
            "leave_type": "Vacaciones (después de 4 años)",
            "from_date": "2025-07-09",
            "to_date": "2025-07-09",
            "status": "Approved",
        },
        {
            "employee": "47",
            "employee_name": "Maria Brenda Bautista Zavala",
            "leave_type": "Permiso sin goce de sueldo",
            "from_date": "2025-07-10",
            "to_date": "2025-07-10",
            "status": "Approved",
        },
        {
            "employee": "47",
            "employee_name": "Maria Brenda Bautista Zavala",
            "leave_type": "Vacaciones (después de 4 años)",
            "from_date": "2025-07-11",
            "to_date": "2025-07-14",
            "status": "Approved",
        },
    ]


class TestDataBuilder:
    """Clase helper para construir datos de prueba"""

    @staticmethod
    def build_leave_application(
        employee, name, leave_type, from_date, to_date, status="Approved"
    ):
        """Construye un permiso individual"""
        return {
            "employee": employee,
            "employee_name": name,
            "leave_type": leave_type,
            "from_date": from_date,
            "to_date": to_date,
            "status": status,
        }

    @staticmethod
    def build_attendance_row(
        employee, dia, horas_esperadas="8:00:00", tipo_retardo="A Tiempo", es_falta=0
    ):
        """Construye una fila de asistencia"""
        return {
            "employee": employee,
            "dia": dia,
            "horas_esperadas": horas_esperadas,
            "tipo_retardo": tipo_retardo,
            "es_falta": es_falta,
        }

    @staticmethod
    def build_dataframe_from_rows(rows):
        """Construye un DataFrame a partir de filas"""
        return pd.DataFrame(rows)
