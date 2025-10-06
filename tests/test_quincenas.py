"""
Tests para validar la funcionalidad de multi-quincena
"""

import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch

import db_postgres_connection as db_conn

# Añadir el directorio raíz al path para importar los módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db_postgres_connection import (
    obtener_horarios_multi_quincena,
    mapear_horarios_por_empleado_multi,
    obtener_horario_empleado,
)


def test_deteccion_quincena_rango_primera():
    """
    Prueba que un rango dentro de la primera quincena solo activa la primera quincena
    Rango 2025-07-01..2025-07-15 → solo primera
    """
    # Simular el análisis de fechas
    fecha_inicio_dt = datetime.strptime("2025-07-01", "%Y-%m-%d")
    fecha_fin_dt = datetime.strptime("2025-07-15", "%Y-%m-%d")

    incluye_primera = False
    incluye_segunda = False

    # Crear un rango de fechas entre inicio y fin
    fecha_actual = fecha_inicio_dt
    while fecha_actual <= fecha_fin_dt:
        if fecha_actual.day <= 15:
            incluye_primera = True
        else:
            incluye_segunda = True
        fecha_actual += timedelta(days=1)

    assert incluye_primera == True
    assert incluye_segunda == False


def test_deteccion_quincena_rango_cruce_quincenas():
    """
    Prueba que un rango que cruza del 15 al 16 activa ambas quincenas
    Rango 2025-07-14..2025-07-17 → cruza quincenas (15→16)
    """
    # Simular el análisis de fechas
    fecha_inicio_dt = datetime.strptime("2025-07-14", "%Y-%m-%d")
    fecha_fin_dt = datetime.strptime("2025-07-17", "%Y-%m-%d")

    incluye_primera = False
    incluye_segunda = False

    # Crear un rango de fechas entre inicio y fin
    fecha_actual = fecha_inicio_dt
    while fecha_actual <= fecha_fin_dt:
        if fecha_actual.day <= 15:
            incluye_primera = True
        else:
            incluye_segunda = True
        fecha_actual += timedelta(days=1)

    assert incluye_primera == True
    assert incluye_segunda == True


def test_deteccion_quincena_rango_cruce_meses():
    """
    Prueba que un rango que cruza meses y quincenas activa ambas quincenas
    Rango 2025-07-10..2025-08-05 → cruza mes y quincena
    """
    # Simular el análisis de fechas
    fecha_inicio_dt = datetime.strptime("2025-07-10", "%Y-%m-%d")
    fecha_fin_dt = datetime.strptime("2025-08-05", "%Y-%m-%d")

    incluye_primera = False
    incluye_segunda = False

    # Crear un rango de fechas entre inicio y fin
    fecha_actual = fecha_inicio_dt
    while fecha_actual <= fecha_fin_dt:
        if fecha_actual.day <= 15:
            incluye_primera = True
        else:
            incluye_segunda = True
        fecha_actual += timedelta(days=1)

    assert incluye_primera == True
    assert incluye_segunda == True


def test_obtener_horarios_multi_quincena():
    """
    Prueba que obtener_horarios_multi_quincena llame a obtener_tabla_horarios
    con los parámetros correctos según las quincenas solicitadas
    """
    with patch("db_postgres_connection.obtener_tabla_horarios") as mock_obtener_tabla:
        # Configurar el mock para devolver valores diferentes según los parámetros
        mock_obtener_tabla.side_effect = lambda sucursal, es_primera, conn, codigos: (
            [
                {
                    "codigo_frappe": "EMP1",
                    "nombre_sucursal": sucursal,
                    "nombre_completo": "Empleado 1",
                }
            ]
            if es_primera
            else [
                {
                    "codigo_frappe": "EMP2",
                    "nombre_sucursal": sucursal,
                    "nombre_completo": "Empleado 2",
                }
            ]
        )

        # Caso 1: Sólo primera quincena
        horarios = obtener_horarios_multi_quincena(
            "Sucursal1",
            "conn-mock",
            ["EMP1", "EMP2"],
            incluye_primera=True,
            incluye_segunda=False,
        )
        assert True in horarios
        assert False not in horarios
        mock_obtener_tabla.assert_called_once_with(
            "Sucursal1", True, "conn-mock", ["EMP1", "EMP2"]
        )
        mock_obtener_tabla.reset_mock()

        # Caso 2: Sólo segunda quincena
        horarios = obtener_horarios_multi_quincena(
            "Sucursal1",
            "conn-mock",
            ["EMP1", "EMP2"],
            incluye_primera=False,
            incluye_segunda=True,
        )
        assert False in horarios
        assert True not in horarios
        mock_obtener_tabla.assert_called_once_with(
            "Sucursal1", False, "conn-mock", ["EMP1", "EMP2"]
        )
        mock_obtener_tabla.reset_mock()

        # Caso 3: Ambas quincenas
        horarios = obtener_horarios_multi_quincena(
            "Sucursal1",
            "conn-mock",
            ["EMP1", "EMP2"],
            incluye_primera=True,
            incluye_segunda=True,
        )
        assert True in horarios
        assert False in horarios
        assert mock_obtener_tabla.call_count == 2
        mock_obtener_tabla.assert_any_call(
            "Sucursal1", True, "conn-mock", ["EMP1", "EMP2"]
        )
        mock_obtener_tabla.assert_any_call(
            "Sucursal1", False, "conn-mock", ["EMP1", "EMP2"]
        )


def test_mapear_horarios_empleado_multi():
    """
    Prueba que mapear_horarios_por_empleado_multi construya correctamente
    el cache con ambas quincenas
    """
    # Datos de prueba para simular resultados de f_tabla_horarios
    horarios_primera = [
        {
            "codigo_frappe": "EMP1",
            "nombre_completo": "Empleado 1",
            "nombre_sucursal": "Sucursal1",
            "Lunes": {
                "horario_entrada": "09:00",
                "horario_salida": "18:00",
                "horas_totales": "9",
            },
            "Martes": {
                "horario_entrada": "09:00",
                "horario_salida": "18:00",
                "horas_totales": "9",
            },
            "Miércoles": None,
            "Jueves": {
                "horario_entrada": "09:00",
                "horario_salida": "18:00",
                "horas_totales": "9",
            },
            "Viernes": {
                "horario_entrada": "09:00",
                "horario_salida": "18:00",
                "horas_totales": "9",
            },
            "Sábado": None,
            "Domingo": None,
        }
    ]

    horarios_segunda = [
        {
            "codigo_frappe": "EMP1",
            "nombre_completo": "Empleado 1",
            "nombre_sucursal": "Sucursal1",
            "Lunes": {
                "horario_entrada": "10:00",
                "horario_salida": "19:00",
                "horas_totales": "9",
            },
            "Martes": {
                "horario_entrada": "10:00",
                "horario_salida": "19:00",
                "horas_totales": "9",
            },
            "Miércoles": {
                "horario_entrada": "10:00",
                "horario_salida": "19:00",
                "horas_totales": "9",
            },
            "Jueves": None,
            "Viernes": {
                "horario_entrada": "10:00",
                "horario_salida": "19:00",
                "horas_totales": "9",
            },
            "Sábado": None,
            "Domingo": None,
        }
    ]

    # Probar con ambas quincenas
    horarios_por_quincena = {True: horarios_primera, False: horarios_segunda}

    cache = mapear_horarios_por_empleado_multi(horarios_por_quincena)

    # Verificar estructura del cache
    assert "EMP1" in cache
    assert True in cache["EMP1"]  # Primera quincena
    assert False in cache["EMP1"]  # Segunda quincena

    # Verificar datos de la primera quincena
    assert 1 in cache["EMP1"][True]  # Lunes
    assert 2 in cache["EMP1"][True]  # Martes
    assert 3 not in cache["EMP1"][True]  # Miércoles (no tiene horario)
    assert cache["EMP1"][True][1]["hora_entrada"] == "09:00"

    # Verificar datos de la segunda quincena
    assert 1 in cache["EMP1"][False]  # Lunes
    assert 3 in cache["EMP1"][False]  # Miércoles
    assert 4 not in cache["EMP1"][False]  # Jueves (no tiene horario)
    assert cache["EMP1"][False][1]["hora_entrada"] == "10:00"


def test_deteccion_cruza_medianoche():
    """
    Prueba que se detecte correctamente cuando un turno cruza la medianoche
    """
    horarios_primera = [
        {
            "codigo_frappe": "EMP1",
            "nombre_completo": "Empleado 1",
            "nombre_sucursal": "Sucursal1",
            "Lunes": {
                "horario_entrada": "22:00",
                "horario_salida": "06:00",
                "horas_totales": "8",
                "cruza_medianoche": True,
            },
            "Martes": None,
            "Miércoles": None,
            "Jueves": None,
            "Viernes": None,
            "Sábado": None,
            "Domingo": None,
        }
    ]

    horarios_por_quincena = {True: horarios_primera}

    cache = mapear_horarios_por_empleado_multi(horarios_por_quincena)

    assert cache["EMP1"][True][1]["cruza_medianoche"] is True


def test_obtener_horario_empleado_multi():
    """
    Prueba que obtener_horario_empleado lea del sub-mapa correcto
    según es_primera_quincena para formato multi-quincena
    """
    db_conn._horario_cache.clear()
    # Crear un cache de prueba con formato multi-quincena
    cache = {
        "EMP1": {
            True: {  # Primera quincena
                1: {
                    "hora_entrada": "09:00",
                    "hora_salida": "18:00",
                    "horas_totales": "9",
                    "cruza_medianoche": False,
                }
            },
            False: {  # Segunda quincena
                1: {
                    "hora_entrada": "10:00",
                    "hora_salida": "19:00",
                    "horas_totales": "9",
                    "cruza_medianoche": False,
                }
            },
        }
    }

    # Caso 1: Obtener horario de primera quincena
    horario = obtener_horario_empleado("EMP1", 1, True, cache)
    assert horario["hora_entrada"] == "09:00"

    # Caso 2: Obtener horario de segunda quincena
    horario = obtener_horario_empleado("EMP1", 1, False, cache)
    assert horario["hora_entrada"] == "10:00"

    # Caso 3: Día sin horario
    horario = obtener_horario_empleado("EMP1", 2, True, cache)
    assert horario is None

    # Caso 4: Empleado no existente
    horario = obtener_horario_empleado("EMP2", 1, True, cache)
    assert horario is None

    # Caso 5: Quincena no existente
    db_conn._horario_cache.clear()
    cache = {"EMP1": {True: {1: {"hora_entrada": "09:00"}}}}
    horario = obtener_horario_empleado("EMP1", 1, False, cache)
    assert horario is None


def test_obtener_horario_empleado_compatible_legacy():
    """
    Prueba que obtener_horario_empleado sea compatible con el formato legacy
    """
    # Crear un cache de prueba con formato legacy
    cache_legacy = {
        "EMP1": {
            1: {
                "hora_entrada": "09:00",
                "hora_salida": "18:00",
                "horas_totales": "9",
                "cruza_medianoche": False,
            }
        }
    }

    # Caso 1: Leer del formato legacy
    horario = obtener_horario_empleado("EMP1", 1, True, cache_legacy)
    assert horario["hora_entrada"] == "09:00"

    # Caso 2: Día sin horario en formato legacy
    horario = obtener_horario_empleado("EMP1", 2, True, cache_legacy)
    assert horario is None
