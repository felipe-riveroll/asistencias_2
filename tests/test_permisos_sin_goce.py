"""
Tests para la funcionalidad de permisos sin goce de sueldo.

Este módulo contiene tests que verifican:
1. Que los permisos sin goce no descuenten horas esperadas
2. Que los permisos normales sí descuenten horas
3. Que se capturen permisos que traslapan el period
4. Funcionalidad completa de permisos de medio día
"""

import pytest
import pandas as pd
from datetime import date

# Importar las funciones del módulo principal
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generar_reporte_optimizado import (
    normalize_leave_type,
    POLITICA_PERMISOS,
    procesar_permisos_empleados,
    ajustar_horas_esperadas_con_permisos,
)


class TestNormalizacion:
    """Tests para la normalización de tipos de permisos."""

    def test_normalize_leave_type_basic(self):
        """Test básico de normalización."""
        assert (
            normalize_leave_type("Permiso Sin Goce De Sueldo")
            == "permiso sin goce de sueldo"
        )
        assert normalize_leave_type("  PERMISO MÉDICO  ") == "permiso medico"
        assert normalize_leave_type("") == ""
        assert normalize_leave_type(None) == ""

    def test_politica_permisos_constants(self):
        """Verificar que las constantes de política están definidas."""
        assert "permiso sin goce de sueldo" in POLITICA_PERMISOS
        assert POLITICA_PERMISOS["permiso sin goce de sueldo"] == "no_ajustar"


class TestProcesarPermisos:
    """Tests para procesamiento de permisos con normalización."""

    def test_procesar_permisos_incluye_normalized(self):
        """Verificar que procesar_permisos_empleados incluye leave_type_normalized."""
        leave_data = [
            {
                "employee": "EMP001",
                "employee_name": "Juan Pérez",
                "leave_type": "Permiso Sin Goce De Sueldo",
                "from_date": "2025-07-15",
                "to_date": "2025-07-15",
                "status": "Approved",
            }
        ]

        resultado = procesar_permisos_empleados(leave_data)

        assert "EMP001" in resultado
        fecha_permiso = date(2025, 7, 15)
        assert fecha_permiso in resultado["EMP001"]

        permiso_info = resultado["EMP001"][fecha_permiso]
        assert "leave_type_normalized" in permiso_info
        assert permiso_info["leave_type_normalized"] == "permiso sin goce de sueldo"
        assert permiso_info["leave_type"] == "Permiso Sin Goce De Sueldo"


class TestPermisosTraslapes:
    """Tests para captura de permisos que traslapan el periodo."""

    def test_permiso_traslapa_inicio_periodo(self):
        """Permiso que empieza antes del periodo pero termina dentro."""
        leave_data = [
            {
                "employee": "EMP001",
                "employee_name": "Juan Pérez",
                "leave_type": "Permiso Normal",
                "from_date": "2025-07-13",  # Antes del periodo
                "to_date": "2025-07-16",  # Dentro del periodo
                "status": "Approved",
            }
        ]

        resultado = procesar_permisos_empleados(leave_data)

        # Debe incluir los días 15 y 16 del periodo
        assert date(2025, 7, 15) in resultado["EMP001"]
        assert date(2025, 7, 16) in resultado["EMP001"]
        # No debe incluir días anteriores al periodo en este test
        # (en la práctica sí los incluiría, pero no los usaríamos)

    def test_permiso_traslapa_fin_periodo(self):
        """Permiso que empieza dentro del periodo pero termina después."""
        leave_data = [
            {
                "employee": "EMP001",
                "employee_name": "Juan Pérez",
                "leave_type": "Permiso Normal",
                "from_date": "2025-07-25",  # Dentro del periodo
                "to_date": "2025-07-30",  # Después del periodo
                "status": "Approved",
            }
        ]

        resultado = procesar_permisos_empleados(leave_data)

        # Debe incluir los días 25, 26, 27, 28 del periodo
        assert date(2025, 7, 25) in resultado["EMP001"]
        assert date(2025, 7, 28) in resultado["EMP001"]


class TestAjusteHorasPermisos:
    """Tests para el ajuste de horas esperadas según tipo de permiso."""

    def create_sample_dataframe(self):
        """Crear un DataFrame de muestra para testing."""
        return pd.DataFrame(
            {
                "employee": ["EMP001", "EMP001", "EMP002"],
                "dia": [date(2025, 7, 15), date(2025, 7, 16), date(2025, 7, 15)],
                "horas_esperadas": ["08:00:00", "08:00:00", "08:00:00"],
                "horas_trabajadas": ["00:00:00", "08:00:00", "00:00:00"],
            }
        )

    def test_permiso_sin_goce_no_descuenta(self):
        """Caso 1: Permiso sin goce en día laboral → es_permiso_sin_goce=True, horas_esperadas no cambia."""
        df = self.create_sample_dataframe()

        permisos_dict = {
            "EMP001": {
                date(2025, 7, 15): {
                    "leave_type": "Permiso Sin Goce De Sueldo",
                    "leave_type_normalized": "permiso sin goce de sueldo",
                    "employee_name": "Juan Pérez",
                }
            }
        }

        cache_horarios = {}  # Mock vacío
        resultado = ajustar_horas_esperadas_con_permisos(
            df, permisos_dict, cache_horarios
        )

        # Verificar que el empleado tiene permiso pero no se descuentan horas
        fila_permiso = resultado[resultado["employee"] == "EMP001"].iloc[0]

        assert fila_permiso["tiene_permiso"] == True
        assert fila_permiso["es_permiso_sin_goce"] == True
        assert fila_permiso["tipo_permiso"] == "Permiso Sin Goce De Sueldo"
        assert fila_permiso["horas_esperadas"] == "08:00:00"  # NO cambió
        assert fila_permiso["horas_descontadas_permiso"] == "00:00:00"  # NO se descontó

    def test_permiso_normal_descuenta(self):
        """Caso 2: Permiso normal → horas_esperadas='00:00:00', horas_descontadas_permiso igual a originales."""
        df = self.create_sample_dataframe()

        permisos_dict = {
            "EMP002": {
                date(2025, 7, 15): {
                    "leave_type": "Permiso Médico",
                    "leave_type_normalized": "permiso médico",
                    "employee_name": "María García",
                }
            }
        }

        cache_horarios = {}  # Mock vacío
        resultado = ajustar_horas_esperadas_con_permisos(
            df, permisos_dict, cache_horarios
        )

        # Verificar que se descuentan las horas (comportamiento actual)
        fila_permiso = resultado[resultado["employee"] == "EMP002"].iloc[0]

        assert fila_permiso["tiene_permiso"] == True
        assert fila_permiso["es_permiso_sin_goce"] == False
        assert fila_permiso["tipo_permiso"] == "Permiso Médico"
        assert fila_permiso["horas_esperadas"] == "00:00:00"  # SÍ cambió
        assert fila_permiso["horas_descontadas_permiso"] == "08:00:00"  # SÍ se descontó

    def test_empleado_sin_permiso(self):
        """Verificar que empleados sin permiso no se ven afectados."""
        df = self.create_sample_dataframe()
        permisos_dict = {}  # Sin permisos
        cache_horarios = {}

        resultado = ajustar_horas_esperadas_con_permisos(
            df, permisos_dict, cache_horarios
        )

        for _, fila in resultado.iterrows():
            assert fila["tiene_permiso"] == False
            assert fila["es_permiso_sin_goce"] == False
            assert fila["tipo_permiso"] is None
            assert fila["horas_esperadas"] == "08:00:00"  # No cambió
            assert fila["horas_descontadas_permiso"] == "00:00:00"


class TestColumnasSeguimiento:
    """Tests para verificar que las nuevas columnas se crean correctamente."""

    def test_columnas_nuevas_creadas(self):
        """Verificar que las nuevas columnas de seguimiento se crean."""
        df = pd.DataFrame(
            {
                "employee": ["EMP001"],
                "dia": [date(2025, 7, 15)],
                "horas_esperadas": ["08:00:00"],
                "horas_trabajadas": ["08:00:00"],
            }
        )

        resultado = ajustar_horas_esperadas_con_permisos(df, {}, {})

        # Verificar que existen las columnas nuevas
        assert "es_permiso_sin_goce" in resultado.columns
        assert "horas_esperadas_originales" in resultado.columns
        assert "tiene_permiso" in resultado.columns
        assert "tipo_permiso" in resultado.columns
        assert "horas_descontadas_permiso" in resultado.columns

        # Verificar valores por defecto
        fila = resultado.iloc[0]
        assert fila["es_permiso_sin_goce"] == False
        assert fila["tiene_permiso"] == False
        assert fila["horas_esperadas_originales"] == "08:00:00"


class TestMedioDia:
    """Tests para la funcionalidad de permisos de medio día."""

    def test_permiso_medio_dia_pendiente(self):
        """Test para verificar que los permisos de medio día funcionan correctamente."""
        df = pd.DataFrame(
            {
                "employee": ["EMP001"],
                "dia": [date(2025, 7, 15)],
                "horas_esperadas": ["08:00:00"],
                "horas_trabajadas": ["04:00:00"],
            }
        )

        permisos_dict = {
            "EMP001": {
                date(2025, 7, 15): {
                    "leave_type": "Permiso Médico",
                    "leave_type_normalized": "permiso médico",
                    "employee_name": "Juan Pérez",
                    "from_date": date(2025, 7, 15),
                    "to_date": date(2025, 7, 15),
                    "status": "Approved",
                    "is_half_day": True,
                    "dias_permiso": 0.5,
                }
            }
        }

        # Ahora que está implementado, esto debería resultar en 4 horas esperadas
        resultado = ajustar_horas_esperadas_con_permisos(df, permisos_dict, {})
        fila = resultado.iloc[0]

        # Verificar que el permiso de medio día funciona correctamente
        assert fila["tiene_permiso"] == True
        assert fila["es_permiso_medio_dia"] == True
        assert fila["tipo_permiso"] == "Permiso Médico"
        assert fila["horas_esperadas"] == "04:00:00"  # Medio día
        assert fila["horas_descontadas_permiso"] == "04:00:00"  # Solo medio día descontado
        assert fila["horas_esperadas_originales"] == "08:00:00"  # Horas originales preservadas

    def test_permiso_medio_dia_con_datos_reales_api(self):
        """Test que simula datos reales de la API con campo half_day."""
        df = pd.DataFrame(
            {
                "employee": ["EMP002"],
                "dia": [date(2025, 7, 16)],
                "horas_esperadas": ["08:00:00"],
                "horas_trabajadas": ["06:00:00"],
            }
        )

        # Simular datos de la API con half_day
        leave_data = [
            {
                "employee": "EMP002",
                "employee_name": "María García",
                "leave_type": "Compensación de tiempo por tiempo",
                "from_date": "2025-07-16",
                "to_date": "2025-07-16",
                "status": "Approved",
                "half_day": 1  # Campo de la API
            }
        ]

        # Procesar permisos usando la función actualizada
        permisos_dict = procesar_permisos_empleados(leave_data)
        
        # Aplicar ajuste de horas
        resultado = ajustar_horas_esperadas_con_permisos(df, permisos_dict, {})
        fila = resultado.iloc[0]

        # Verificar que se procesó correctamente como medio día
        assert fila["tiene_permiso"] == True
        assert fila["es_permiso_medio_dia"] == True
        assert fila["tipo_permiso"] == "Compensación de tiempo por tiempo"
        assert fila["horas_esperadas"] == "04:00:00"  # Medio día
        assert fila["horas_descontadas_permiso"] == "04:00:00"  # Solo medio día descontado

    def test_permiso_dia_completo_vs_medio_dia(self):
        """Test para comparar permisos de día completo vs medio día."""
        df = pd.DataFrame(
            {
                "employee": ["EMP003", "EMP004"],
                "dia": [date(2025, 7, 17), date(2025, 7, 17)],
                "horas_esperadas": ["08:00:00", "08:00:00"],
                "horas_trabajadas": ["08:00:00", "04:00:00"],
            }
        )

        permisos_dict = {
            "EMP003": {
                date(2025, 7, 17): {
                    "leave_type": "Vacaciones",
                    "leave_type_normalized": "vacaciones",
                    "employee_name": "Carlos López",
                    "from_date": date(2025, 7, 17),
                    "to_date": date(2025, 7, 17),
                    "status": "Approved",
                    "is_half_day": False,
                    "dias_permiso": 1.0,
                }
            },
            "EMP004": {
                date(2025, 7, 17): {
                    "leave_type": "Permiso Médico",
                    "leave_type_normalized": "permiso médico",
                    "employee_name": "Ana Martínez",
                    "from_date": date(2025, 7, 17),
                    "to_date": date(2025, 7, 17),
                    "status": "Approved",
                    "is_half_day": True,
                    "dias_permiso": 0.5,
                }
            }
        }

        resultado = ajustar_horas_esperadas_con_permisos(df, permisos_dict, {})
        
        # Verificar permiso de día completo
        fila_dia_completo = resultado[resultado["employee"] == "EMP003"].iloc[0]
        assert fila_dia_completo["es_permiso_medio_dia"] == False
        assert fila_dia_completo["horas_esperadas"] == "00:00:00"  # Día completo
        assert fila_dia_completo["horas_descontadas_permiso"] == "08:00:00"  # Todo el día

        # Verificar permiso de medio día
        fila_medio_dia = resultado[resultado["employee"] == "EMP004"].iloc[0]
        assert fila_medio_dia["es_permiso_medio_dia"] == True
        assert fila_medio_dia["horas_esperadas"] == "04:00:00"  # Medio día
        assert fila_medio_dia["horas_descontadas_permiso"] == "04:00:00"  # Solo medio día


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
