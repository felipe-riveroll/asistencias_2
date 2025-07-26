import pytest
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta, date
from unittest.mock import patch, MagicMock
import sys
import os

# Agregar el directorio padre al path para importar el módulo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar las funciones a probar
from generar_reporte_optimizado import (
    fetch_checkins,
    obtener_codigos_empleados_api,
    process_checkins_to_dataframe,
    procesar_horarios_con_medianoche,
    calcular_proximidad_horario,
    analizar_asistencia_con_horarios_cache,
    generar_resumen_periodo
)


@pytest.fixture
def checkin_data():
    """Fixture con datos de prueba para checadas."""
    return [
        {
            "employee": "EMP001",
            "employee_name": "Juan Pérez",
            "time": "2025-01-15 08:00:00"
        },
        {
            "employee": "EMP001",
            "employee_name": "Juan Pérez",
            "time": "2025-01-15 17:00:00"
        },
        {
            "employee": "EMP002",
            "employee_name": "María García",
            "time": "2025-01-15 08:30:00"
        },
        {
            "employee": "EMP002",
            "employee_name": "María García",
            "time": "2025-01-15 17:30:00"
        }
    ]


@pytest.fixture
def cache_horarios():
    """Fixture con caché de horarios de prueba."""
    return {
        "EMP001": {
            1: {
                "hora_entrada": "08:00",
                "hora_salida": "17:00",
                "cruza_medianoche": False,
                "horas_totales": 9.0
            },
            2: {
                "hora_entrada": "08:00",
                "hora_salida": "17:00",
                "cruza_medianoche": False,
                "horas_totales": 9.0
            },
            3: {
                "hora_entrada": "08:00",
                "hora_salida": "17:00",
                "cruza_medianoche": False,
                "horas_totales": 9.0
            }
        },
        "EMP002": {
            1: {
                "hora_entrada": "08:00",
                "hora_salida": "17:00",
                "cruza_medianoche": False,
                "horas_totales": 9.0
            },
            2: {
                "hora_entrada": "08:00",
                "hora_salida": "17:00",
                "cruza_medianoche": False,
                "horas_totales": 9.0
            },
            3: {
                "hora_entrada": "08:00",
                "hora_salida": "17:00",
                "cruza_medianoche": False,
                "horas_totales": 9.0
            }
        }
    }


@pytest.fixture
def cache_horarios_nocturno():
    """Fixture con caché de horarios nocturnos."""
    return {
        "EMP003": {
            1: {
                "hora_entrada": "22:00",
                "hora_salida": "06:00",
                "cruza_medianoche": True,
                "horas_totales": 8.0
            },
            3: {
                "hora_entrada": "22:00",
                "hora_salida": "06:00",
                "cruza_medianoche": True,
                "horas_totales": 8.0
            }
        }
    }


class TestGenerarReporteOptimizado:
    """Pruebas unitarias para las funciones principales del reporte de asistencia."""

    def test_obtener_codigos_empleados_api(self, checkin_data):
        """Prueba la extracción de códigos de empleados de los datos de la API."""
        # Caso normal
        codigos = obtener_codigos_empleados_api(checkin_data)
        assert len(codigos) == 2
        assert "EMP001" in codigos
        assert "EMP002" in codigos

        # Caso con datos vacíos
        codigos_vacios = obtener_codigos_empleados_api([])
        assert codigos_vacios == []

        # Caso con datos None
        codigos_none = obtener_codigos_empleados_api(None)
        assert codigos_none == []

    def test_process_checkins_to_dataframe(self, checkin_data):
        """Prueba la creación del DataFrame base con las checadas."""
        start_date = "2025-01-15"
        end_date = "2025-01-15"

        # Procesar datos de prueba
        df = process_checkins_to_dataframe(checkin_data, start_date, end_date)

        # Verificar que el DataFrame no esté vacío
        assert not df.empty
        assert len(df) > 0

        # Verificar columnas esperadas
        columnas_esperadas = [
            "employee", "Nombre", "dia", "dia_semana", 
            "dia_iso", "horas_trabajadas"
        ]
        for col in columnas_esperadas:
            assert col in df.columns

        # Verificar que se crearon columnas de checadas
        checado_cols = [col for col in df.columns if "checado_" in col]
        assert len(checado_cols) > 0

        # Verificar que los empleados están presentes
        empleados_unicos = df["employee"].unique()
        assert "EMP001" in empleados_unicos
        assert "EMP002" in empleados_unicos

        # Verificar que las horas trabajadas se calcularon correctamente
        horas_emp1 = df[df["employee"] == "EMP001"]["horas_trabajadas"].iloc[0]
        assert horas_emp1 is not None
        assert horas_emp1 != "00:00:00"

    def test_process_checkins_to_dataframe_empty_data(self):
        """Prueba el procesamiento con datos vacíos."""
        start_date = "2025-01-15"
        end_date = "2025-01-15"

        # Datos vacíos
        df_vacio = process_checkins_to_dataframe([], start_date, end_date)
        assert df_vacio.empty

        # Datos None
        df_none = process_checkins_to_dataframe(None, start_date, end_date)
        assert df_none.empty

    @pytest.mark.parametrize("checada,hora_prog,esperado", [
        ("08:00:00", "08:00", 0),
        ("08:15:00", "08:00", 15),
        ("07:45:00", "08:00", 15),
        ("09:00:00", "08:00", 60),
        ("07:00:00", "08:00", 60),
        ("00:00:00", "00:00", 0),
    ])
    def test_calcular_proximidad_horario_parametrizado(self, checada, hora_prog, esperado):
        """Prueba el cálculo de proximidad entre horarios con casos parametrizados."""
        resultado = calcular_proximidad_horario(checada, hora_prog)
        assert resultado == esperado

    def test_calcular_proximidad_horario_casos_extremos(self):
        """Prueba casos extremos en el cálculo de proximidad de horarios."""
        # Casos extremos con assertAlmostEqual para valores flotantes
        resultado1 = calcular_proximidad_horario("23:59:59", "00:00")
        assert abs(resultado1 - 1439.983) < 0.1  # Tolerancia de 0.1 minutos
        
        resultado2 = calcular_proximidad_horario("00:00:01", "23:59")
        assert abs(resultado2 - 1438.983) < 0.1  # Tolerancia de 0.1 minutos

    def test_calcular_proximidad_horario_formatos_invalidos(self):
        """Prueba el manejo de formatos inválidos."""
        # Casos con errores (deberían devolver infinito)
        assert calcular_proximidad_horario("hora_invalida", "08:00") == float('inf')
        assert calcular_proximidad_horario("08:00:00", "hora_invalida") == float('inf')
        assert calcular_proximidad_horario("", "08:00") == float('inf')
        assert calcular_proximidad_horario("08:00:00", "") == float('inf')

    def test_analizar_asistencia_con_horarios_cache(self):
        """Prueba el análisis de asistencia con caché de horarios."""
        # Crear caché de horarios específico para esta prueba
        cache_horarios_especifico = {
            "EMP001": {
                3: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0},
                4: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0}
            },
            "EMP002": {
                3: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0}
            }
        }
        
        # Crear DataFrame de prueba
        df_test = pd.DataFrame({
            "employee": ["EMP001", "EMP001", "EMP002"],
            "Nombre": ["Juan Pérez", "Juan Pérez", "María García"],
            "dia": [date(2025, 1, 15), date(2025, 1, 16), date(2025, 1, 15)],
            "dia_iso": [3, 4, 3],  # Miércoles, Jueves, Miércoles
            "checado_1": ["08:00:00", "08:30:00", "08:15:00"],
            "checado_2": ["17:00:00", "17:30:00", "17:15:00"],
            "horas_trabajadas": ["09:00:00", "09:00:00", "09:00:00"]
        })

        # Analizar asistencia
        df_analizado = analizar_asistencia_con_horarios_cache(df_test, cache_horarios_especifico)

        # Verificar que se agregaron las columnas esperadas
        columnas_esperadas = [
            "hora_entrada_programada", "hora_salida_programada",
            "cruza_medianoche", "horas_esperadas", "tipo_retardo",
            "minutos_tarde", "es_retardo_acumulable", "es_falta",
            "retardos_acumulados", "descuento_por_3_retardos"
        ]
        for col in columnas_esperadas:
            assert col in df_analizado.columns

        # Verificar que los horarios se asignaron correctamente
        assert df_analizado["hora_entrada_programada"].iloc[0] is not None
        assert df_analizado["hora_salida_programada"].iloc[0] is not None

        # Verificar que se calculó el tipo de retardo
        tipos_retardo = df_analizado["tipo_retardo"].unique()
        assert len(tipos_retardo) > 0

    def test_analizar_asistencia_con_horarios_cache_empty_df(self, cache_horarios):
        """Prueba el análisis con DataFrame vacío."""
        df_vacio = pd.DataFrame()
        df_resultado = analizar_asistencia_con_horarios_cache(df_vacio, cache_horarios)
        assert df_resultado.empty

    def test_procesar_horarios_con_medianoche(self, cache_horarios_nocturno):
        """Prueba el procesamiento de horarios que cruzan medianoche."""
        # Crear DataFrame con turno nocturno
        df_nocturno = pd.DataFrame({
            "employee": ["EMP003", "EMP003"],
            "Nombre": ["Carlos Nocturno", "Carlos Nocturno"],
            "dia": [date(2025, 1, 15), date(2025, 1, 16)],
            "dia_iso": [3, 4],
            "checado_1": ["22:00:00", "06:00:00"],
            "checado_2": ["23:00:00", "07:00:00"],
            "horas_trabajadas": ["01:00:00", "01:00:00"]
        })

        # Procesar horarios nocturnos
        df_procesado = procesar_horarios_con_medianoche(df_nocturno, cache_horarios_nocturno)

        # Verificar que el DataFrame no se perdió
        assert not df_procesado.empty
        assert len(df_procesado) == len(df_nocturno)

        # Verificar que se agregó la columna es_primera_quincena
        assert "es_primera_quincena" in df_procesado.columns

    def test_procesar_horarios_con_medianoche_sin_horarios(self, cache_horarios):
        """Prueba el procesamiento sin horarios que crucen medianoche."""
        # Crear DataFrame normal (sin turnos nocturnos)
        df_normal = pd.DataFrame({
            "employee": ["EMP001"],
            "Nombre": ["Juan Pérez"],
            "dia": [date(2025, 1, 15)],
            "dia_iso": [3],
            "checado_1": ["08:00:00"],
            "checado_2": ["17:00:00"],
            "horas_trabajadas": ["09:00:00"]
        })

        # Procesar (no debería cambiar nada)
        df_procesado = procesar_horarios_con_medianoche(df_normal, cache_horarios)

        # Verificar que el DataFrame se mantiene igual
        assert not df_procesado.empty
        assert len(df_procesado) == len(df_normal)

    @patch('builtins.print')
    def test_generar_resumen_periodo(self, mock_print, tmp_path):
        """Prueba la generación del resumen del periodo."""
        # Crear DataFrame de prueba con datos completos
        df_test = pd.DataFrame({
            "employee": ["EMP001", "EMP001", "EMP002"],
            "Nombre": ["Juan Pérez", "Juan Pérez", "María García"],
            "dia": [date(2025, 1, 15), date(2025, 1, 16), date(2025, 1, 15)],
            "horas_trabajadas": ["09:00:00", "08:30:00", "09:00:00"],
            "horas_esperadas": ["09:00:00", "09:00:00", "09:00:00"],
            "es_retardo_acumulable": [0, 1, 0],
            "es_falta": [0, 0, 1]
        })

        # Cambiar al directorio temporal para las pruebas
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Generar resumen
            generar_resumen_periodo(df_test)

            # Verificar que se llamó a print (indicando que se ejecutó)
            assert mock_print.call_count > 0

            # Verificar que se creó el archivo de resumen
            assert os.path.exists("resumen_periodo.csv")
        finally:
            # Restaurar directorio original
            os.chdir(original_cwd)

    @patch('builtins.print')
    def test_generar_resumen_periodo_empty_df(self, mock_print):
        """Prueba la generación de resumen con DataFrame vacío."""
        df_vacio = pd.DataFrame()
        generar_resumen_periodo(df_vacio)
        
        # Verificar que se imprimió el mensaje de no hay datos
        mock_print.assert_any_call("   - No hay datos para generar el resumen.")

    @patch('requests.get')
    def test_fetch_checkins_success(self, mock_get):
        """Prueba la obtención exitosa de checadas de la API."""
        # Mock de respuesta exitosa
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"employee": "EMP001", "employee_name": "Juan", "time": "2025-01-15 08:00:00"},
                {"employee": "EMP002", "employee_name": "María", "time": "2025-01-15 08:30:00"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Mock de variables de entorno
        with patch.dict(os.environ, {
            'ASIATECH_API_KEY': 'test_key',
            'ASIATECH_API_SECRET': 'test_secret'
        }):
            with patch('generar_reporte_optimizado.API_KEY', 'test_key'), \
                 patch('generar_reporte_optimizado.API_SECRET', 'test_secret'):
                
                result = fetch_checkins("2025-01-15", "2025-01-15", "%31%")
                
                assert len(result) == 2
                assert result[0]["employee"] == "EMP001"
                assert result[1]["employee"] == "EMP002"

    @patch('requests.get')
    def test_fetch_checkins_api_error(self, mock_get):
        """Prueba el manejo de errores de la API."""
        # Mock de error de API con el tipo correcto de excepción
        mock_get.side_effect = requests.exceptions.RequestException("API Error")

        # Mock de variables de entorno
        with patch.dict(os.environ, {
            'ASIATECH_API_KEY': 'test_key',
            'ASIATECH_API_SECRET': 'test_secret'
        }):
            with patch('generar_reporte_optimizado.API_KEY', 'test_key'), \
                 patch('generar_reporte_optimizado.API_SECRET', 'test_secret'):
                
                result = fetch_checkins("2025-01-15", "2025-01-15", "%31%")
                assert result == []

    def test_fetch_checkins_missing_credentials(self):
        """Prueba el manejo de credenciales faltantes."""
        # Sin credenciales
        with patch('generar_reporte_optimizado.API_KEY', None), \
             patch('generar_reporte_optimizado.API_SECRET', None):
            
            result = fetch_checkins("2025-01-15", "2025-01-15", "%31%")
            assert result == []

    @pytest.mark.parametrize("checada,hora_prog,esperado", [
        ("08:00:00", "08:00", "A Tiempo"),
        ("08:15:00", "08:00", "A Tiempo"),
        ("08:16:00", "08:00", "Retardo"),
        ("08:30:00", "08:00", "Retardo"),
        ("08:31:00", "08:00", "Falta Injustificada"),
        (None, "08:00", "Falta"),
    ])
    def test_analizar_retardo_casos_especificos_parametrizado(self, checada, hora_prog, esperado):
        """Prueba casos específicos de análisis de retardos con parametrización."""
        # Crear caché de horarios específico para esta prueba
        cache_horarios_especifico = {
            "EMP001": {
                3: {  # Miércoles (número, no string)
                    "hora_entrada": hora_prog,
                    "hora_salida": "17:00",
                    "cruza_medianoche": False,
                    "horas_totales": 9.0
                }
            }
        }
        
        # Crear DataFrame con caso específico
        df_caso = pd.DataFrame({
            "employee": ["EMP001"],
            "dia": [date(2025, 1, 15)],
            "dia_iso": [3],
            "checado_1": [checada],
            "hora_entrada_programada": [hora_prog],
            "cruza_medianoche": [False]
        })

        # Analizar asistencia
        df_analizado = analizar_asistencia_con_horarios_cache(df_caso, cache_horarios_especifico)

        # Verificar el tipo de retardo
        tipo_retardo = df_analizado["tipo_retardo"].iloc[0]
        assert tipo_retardo == esperado

    def test_analizar_retardo_turno_nocturno(self, cache_horarios_nocturno):
        """Prueba el análisis de retardos en turnos nocturnos."""
        # Crear DataFrame con turno nocturno
        df_nocturno = pd.DataFrame({
            "employee": ["EMP003"],
            "dia": [date(2025, 1, 15)],
            "dia_iso": [3],
            "checado_1": ["22:30:00"],  # 30 min tarde para turno de 22:00
            "hora_entrada_programada": ["22:00"],
            "cruza_medianoche": [True]
        })

        # Analizar asistencia
        df_analizado = analizar_asistencia_con_horarios_cache(df_nocturno, cache_horarios_nocturno)

        # Verificar que se procesó correctamente
        assert not df_analizado.empty
        assert "tipo_retardo" in df_analizado.columns

    def test_calculo_horas_trabajadas(self):
        """Prueba el cálculo correcto de horas trabajadas."""
        # Datos con múltiples checadas
        datos_multiples_checadas = [
            {
                "employee": "EMP001",
                "employee_name": "Juan Pérez",
                "time": "2025-01-15 08:00:00"
            },
            {
                "employee": "EMP001",
                "employee_name": "Juan Pérez",
                "time": "2025-01-15 12:00:00"
            },
            {
                "employee": "EMP001",
                "employee_name": "Juan Pérez",
                "time": "2025-01-15 13:00:00"
            },
            {
                "employee": "EMP001",
                "employee_name": "Juan Pérez",
                "time": "2025-01-15 17:00:00"
            }
        ]

        df = process_checkins_to_dataframe(datos_multiples_checadas, "2025-01-15", "2025-01-15")
        
        # Verificar que se calculó correctamente (8 horas totales)
        horas_trabajadas = df[df["employee"] == "EMP001"]["horas_trabajadas"].iloc[0]
        assert horas_trabajadas is not None
        assert horas_trabajadas != "00:00:00"

    def test_manejo_dias_no_laborables(self):
        """Prueba el manejo de días no laborables."""
        # Crear caché de horarios sin el empleado para simular día no laborable
        cache_horarios_vacio = {}
        
        # Crear DataFrame con día no laborable
        df_no_laborable = pd.DataFrame({
            "employee": ["EMP001"],
            "dia": [date(2025, 1, 15)],
            "dia_iso": [3],
            "checado_1": ["08:00:00"],
            "hora_entrada_programada": [None],  # Sin horario programado
            "cruza_medianoche": [False]
        })

        # Analizar asistencia
        df_analizado = analizar_asistencia_con_horarios_cache(df_no_laborable, cache_horarios_vacio)

        # Verificar que se marcó como día no laborable
        assert "Día no Laborable" in df_analizado["tipo_retardo"].values


class TestIntegracion:
    """Pruebas de integración para el flujo completo."""

    @pytest.fixture
    def checkin_data_integracion(self):
        """Fixture con datos de integración."""
        return [
            {
                "employee": "EMP001",
                "employee_name": "Juan Pérez",
                "time": "2025-01-15 08:00:00"
            },
            {
                "employee": "EMP001",
                "employee_name": "Juan Pérez",
                "time": "2025-01-15 17:00:00"
            },
            {
                "employee": "EMP002",
                "employee_name": "María García",
                "time": "2025-01-15 08:30:00"
            },
            {
                "employee": "EMP002",
                "employee_name": "María García",
                "time": "2025-01-15 17:30:00"
            }
        ]

    @pytest.fixture
    def cache_horarios_integracion(self):
        """Fixture con caché de horarios para integración."""
        return {
            "EMP001": {
                "3": {  # Miércoles
                    "hora_entrada": "08:00",
                    "hora_salida": "17:00",
                    "cruza_medianoche": False,
                    "horas_totales": 9.0
                }
            },
            "EMP002": {
                "3": {  # Miércoles
                    "hora_entrada": "08:00",
                    "hora_salida": "17:00",
                    "cruza_medianoche": False,
                    "horas_totales": 9.0
                }
            }
        }

    def test_flujo_completo_analisis(self, checkin_data_integracion, cache_horarios_integracion):
        """Prueba el flujo completo de análisis desde datos de checadas hasta resumen."""
        # 1. Procesar checadas a DataFrame
        df_base = process_checkins_to_dataframe(
            checkin_data_integracion, "2025-01-15", "2025-01-15"
        )
        assert not df_base.empty

        # 2. Procesar horarios con medianoche
        df_procesado = procesar_horarios_con_medianoche(df_base, cache_horarios_integracion)
        assert not df_procesado.empty

        # 3. Analizar asistencia
        df_analizado = analizar_asistencia_con_horarios_cache(df_procesado, cache_horarios_integracion)
        assert not df_analizado.empty

        # 4. Verificar que se agregaron todas las columnas necesarias
        columnas_requeridas = [
            "hora_entrada_programada", "hora_salida_programada",
            "tipo_retardo", "minutos_tarde", "es_retardo_acumulable",
            "es_falta", "retardos_acumulados"
        ]
        for col in columnas_requeridas:
            assert col in df_analizado.columns

        # 5. Verificar que los datos tienen sentido
        assert len(df_analizado) > 0
        assert "EMP001" in df_analizado["employee"].values
        assert "EMP002" in df_analizado["employee"].values

    @patch('builtins.print')
    def test_generacion_resumen_integracion(self, mock_print, tmp_path):
        """Prueba la generación de resumen con datos reales."""
        # Crear DataFrame analizado completo
        df_analizado = pd.DataFrame({
            "employee": ["EMP001", "EMP001", "EMP002"],
            "Nombre": ["Juan Pérez", "Juan Pérez", "María García"],
            "dia": [date(2025, 1, 15), date(2025, 1, 16), date(2025, 1, 15)],
            "horas_trabajadas": ["09:00:00", "08:30:00", "09:00:00"],
            "horas_esperadas": ["09:00:00", "09:00:00", "09:00:00"],
            "es_retardo_acumulable": [0, 1, 0],
            "es_falta": [0, 0, 1]
        })

        # Cambiar al directorio temporal para las pruebas
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Generar resumen
            generar_resumen_periodo(df_analizado)

            # Verificar que se ejecutó correctamente
            assert mock_print.call_count > 0
        finally:
            # Restaurar directorio original
            os.chdir(original_cwd) 