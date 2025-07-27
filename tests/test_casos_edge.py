import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from unittest.mock import patch, MagicMock
import sys
import os

# Agregar el directorio padre al path para importar el módulo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar las funciones a probar
from generar_reporte_optimizado import (
    process_checkins_to_dataframe,
    procesar_horarios_con_medianoche,
    calcular_proximidad_horario,
    analizar_asistencia_con_horarios_cache,
    generar_resumen_periodo
)


@pytest.fixture
def cache_horarios_edge():
    """Fixture con caché de horarios para casos edge."""
    return {
        "EMP001": {
            1: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0},
            2: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0},
            3: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0},
            4: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0},
            5: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0},
            6: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0},
            7: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0}
        }
    }


class TestCasosEdge:
    """Pruebas para casos edge y situaciones límite del sistema de reportes."""

    @pytest.mark.parametrize("checada,hora_prog,esperado", [
        ("08:00:00", "08:00", 0),
        ("08:01:00", "08:00", 1),
        ("07:59:00", "08:00", 1),
        ("00:00:00", "00:00", 0),
    ])
    def test_calcular_proximidad_horario_casos_edge(self, checada, hora_prog, esperado):
        """Prueba casos edge en el cálculo de proximidad de horarios."""
        resultado = calcular_proximidad_horario(checada, hora_prog)
        assert resultado == esperado

    def test_calcular_proximidad_horario_casos_extremos(self):
        """Prueba casos extremos en el cálculo de proximidad de horarios."""
        # Casos extremos con assertAlmostEqual para valores flotantes
        resultado1 = calcular_proximidad_horario("23:59:59", "00:00")
        assert abs(resultado1 - 1439.983) < 0.1  # Tolerancia de 0.1 minutos
        
        resultado2 = calcular_proximidad_horario("00:00:01", "23:59")
        assert abs(resultado2 - 1438.983) < 0.1  # Tolerancia de 0.1 minutos

    @pytest.mark.parametrize("checada,hora_prog", [
        ("", "08:00"),
        ("08:00:00", ""),
        (None, "08:00"),
        ("08:00:00", None),
        ("hora_invalida", "08:00"),
        ("08:00:00", "hora_invalida"),
    ])
    def test_calcular_proximidad_horario_formatos_invalidos(self, checada, hora_prog):
        """Prueba el manejo de formatos inválidos."""
        resultado = calcular_proximidad_horario(checada, hora_prog)
        assert resultado == float('inf')

    def test_process_checkins_to_dataframe_solo_una_checada(self):
        """Prueba el procesamiento cuando un empleado solo tiene una checada."""
        datos_una_checada = [
            {
                "employee": "EMP001",
                "employee_name": "Juan Pérez",
                "time": "2025-01-15 08:00:00"
            }
        ]

        df = process_checkins_to_dataframe(datos_una_checada, "2025-01-15", "2025-01-15")
        
        # Verificar que se procesó correctamente
        assert not df.empty
        assert len(df) == 1
        
        # Verificar que las horas trabajadas son 0 (solo una checada)
        horas_trabajadas = df["horas_trabajadas"].iloc[0]
        assert horas_trabajadas == "00:00:00"

    def test_process_checkins_to_dataframe_muchas_checadas(self):
        """Prueba el procesamiento con muchas checadas en un día."""
        datos_muchas_checadas = [
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 08:00:00"},
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 12:00:00"},
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 13:00:00"},
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 15:00:00"},
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 17:00:00"},
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 18:00:00"},
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 19:00:00"},
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 20:00:00"},
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 21:00:00"},
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 22:00:00"}
        ]

        df = process_checkins_to_dataframe(datos_muchas_checadas, "2025-01-15", "2025-01-15")
        
        # Verificar que se procesó correctamente
        assert not df.empty
        
        # Verificar que se crearon columnas para todas las checadas
        checado_cols = [col for col in df.columns if "checado_" in col]
        assert len(checado_cols) >= 9  # Al menos 9 checadas
        
        # Verificar que las horas trabajadas se calcularon correctamente
        horas_trabajadas = df["horas_trabajadas"].iloc[0]
        assert horas_trabajadas != "00:00:00"

    def test_process_checkins_to_dataframe_checadas_invertidas(self):
        """Prueba el procesamiento cuando las checadas están en orden invertido."""
        datos_invertidos = [
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 17:00:00"},
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 08:00:00"}
        ]

        df = process_checkins_to_dataframe(datos_invertidos, "2025-01-15", "2025-01-15")
        
        # Verificar que se procesó correctamente
        assert not df.empty
        
        # Verificar que las horas trabajadas se calcularon correctamente
        horas_trabajadas = df["horas_trabajadas"].iloc[0]
        assert horas_trabajadas != "00:00:00"

    @pytest.mark.parametrize("checada,hora_prog,esperado", [
        ("08:15:00", "08:00", "A Tiempo"),
        ("08:16:00", "08:00", "Retardo"),
        ("08:30:00", "08:00", "Retardo"),
        ("08:31:00", "08:00", "Falta Injustificada"),
    ])
    def test_analizar_asistencia_retardos_limite(self, checada, hora_prog, esperado):
        """Prueba los límites exactos de la clasificación de retardos."""
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

    def test_analizar_asistencia_checadas_antes_horario(self):
        """Prueba el análisis cuando las checadas son antes del horario programado."""
        # Crear caché de horarios específico para esta prueba
        cache_horarios_especifico = {
            "EMP001": {3: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0}},
            "EMP002": {3: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0}},
            "EMP003": {3: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0}}
        }
        
        df_antes = pd.DataFrame({
            "employee": ["EMP001", "EMP002", "EMP003"],
            "dia": [date(2025, 1, 15)] * 3,
            "dia_iso": [3] * 3,
            "checado_1": ["07:30:00", "07:45:00", "07:00:00"],
            "hora_entrada_programada": ["08:00", "08:00", "08:00"],
            "cruza_medianoche": [False, False, False]
        })

        df_analizado = analizar_asistencia_con_horarios_cache(df_antes, cache_horarios_especifico)

        # Todas deberían ser "A Tiempo" (llegada temprana)
        tipos_retardo = df_analizado["tipo_retardo"].tolist()
        for tipo in tipos_retardo:
            assert tipo == "A Tiempo"

    def test_analizar_asistencia_turno_nocturno_casos_edge(self, cache_horarios_edge):
        """Prueba casos edge en turnos nocturnos."""
        cache_nocturno_edge = {
            "EMP001": {
                "1": {
                    "hora_entrada": "22:00",
                    "hora_salida": "06:00",
                    "cruza_medianoche": True,
                    "horas_totales": 8.0
                },
                "3": {
                    "hora_entrada": "22:00",
                    "hora_salida": "06:00",
                    "cruza_medianoche": True,
                    "horas_totales": 8.0
                }
            }
        }

        # Caso: Checada antes de medianoche
        df_nocturno_antes = pd.DataFrame({
            "employee": ["EMP001"],
            "dia": [date(2025, 1, 15)],
            "dia_iso": [3],
            "checado_1": ["21:30:00"],
            "hora_entrada_programada": ["22:00"],
            "cruza_medianoche": [True]
        })

        df_analizado = analizar_asistencia_con_horarios_cache(df_nocturno_antes, cache_nocturno_edge)
        assert not df_analizado.empty

        # Caso: Checada después de medianoche
        df_nocturno_despues = pd.DataFrame({
            "employee": ["EMP001"],
            "dia": [date(2025, 1, 15)],
            "dia_iso": [3],
            "checado_1": ["06:30:00"],
            "hora_entrada_programada": ["22:00"],
            "cruza_medianoche": [True]
        })

        df_analizado = analizar_asistencia_con_horarios_cache(df_nocturno_despues, cache_nocturno_edge)
        assert not df_analizado.empty

    def test_procesar_horarios_con_medianoche_datos_incompletos(self, cache_horarios_edge):
        """Prueba el procesamiento con datos incompletos en turnos nocturnos."""
        df_incompleto = pd.DataFrame({
            "employee": ["EMP001"],
            "Nombre": ["Juan Pérez"],
            "dia": [date(2025, 1, 15)],
            "dia_iso": [3],
            "checado_1": ["22:00:00"],
            # Sin checado_2
            "horas_trabajadas": ["00:00:00"]
        })

        cache_nocturno = {
            "EMP001": {
                "3": {
                    "hora_entrada": "22:00",
                    "hora_salida": "06:00",
                    "cruza_medianoche": True,
                    "horas_totales": 8.0
                }
            }
        }

        df_procesado = procesar_horarios_con_medianoche(df_incompleto, cache_nocturno)
        
        # Verificar que no se perdió el DataFrame
        assert not df_procesado.empty
        assert len(df_procesado) == len(df_incompleto)

    @patch('builtins.print')
    def test_generar_resumen_periodo_datos_negativos(self, mock_print, tmp_path):
        """Prueba la generación de resumen con diferencias negativas de horas."""
        df_negativo = pd.DataFrame({
            "employee": ["EMP001", "EMP002"],
            "Nombre": ["Juan Pérez", "María García"],
            "dia": [date(2025, 1, 15), date(2025, 1, 15)],
            "horas_trabajadas": ["07:00:00", "06:00:00"],  # Menos horas trabajadas
            "horas_esperadas": ["09:00:00", "09:00:00"],   # Más horas esperadas
            "es_retardo_acumulable": [1, 0],
            "es_falta": [0, 1]
        })

        # Cambiar al directorio temporal para las pruebas
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            generar_resumen_periodo(df_negativo)

            # Verificar que se creó el archivo
            assert os.path.exists("resumen_periodo.csv")

            # Leer el archivo para verificar que las diferencias negativas se procesaron
            df_resumen = pd.read_csv("resumen_periodo.csv")
            assert not df_resumen.empty
            for col in [
                "employee",
                "Nombre",
                "total_horas",
                "total_faltas",
                "diferencia_HHMMSS",
            ]:
                assert col in df_resumen.columns
        finally:
            # Restaurar directorio original
            os.chdir(original_cwd)

    @patch('builtins.print')
    def test_generar_resumen_periodo_datos_extremos(self, mock_print, tmp_path):
        """Prueba la generación de resumen con datos extremos."""
        df_extremo = pd.DataFrame({
            "employee": ["EMP001"],
            "Nombre": ["Juan Pérez"],
            "dia": [date(2025, 1, 15)],
            "horas_trabajadas": ["24:00:00"],  # 24 horas trabajadas
            "horas_esperadas": ["08:00:00"],   # 8 horas esperadas
            "es_retardo_acumulable": [0],
            "es_falta": [0]
        })

        # Cambiar al directorio temporal para las pruebas
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            generar_resumen_periodo(df_extremo)

            # Verificar que se creó el archivo
            assert os.path.exists("resumen_periodo.csv")

            # Leer el archivo para verificar que se procesó correctamente
            df_resumen = pd.read_csv("resumen_periodo.csv")
            assert not df_resumen.empty
            required = [
                "total_horas_trabajadas",
                "total_horas_esperadas",
                "total_horas",
                "total_retardos",
                "diferencia_HHMMSS",
            ]
            for col in required:
                assert col in df_resumen.columns
        finally:
            # Restaurar directorio original
            os.chdir(original_cwd)

    def test_analizar_asistencia_datos_nulos(self):
        """Prueba el análisis con datos nulos o faltantes."""
        # Crear caché de horarios específico para esta prueba
        cache_horarios_especifico = {
            "EMP001": {3: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0}},
            "EMP002": {3: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0}}
            # EMP003 no está en el caché para simular día no laborable
        }
        
        df_nulos = pd.DataFrame({
            "employee": ["EMP001", "EMP002", "EMP003"],
            "dia": [date(2025, 1, 15)] * 3,
            "dia_iso": [3] * 3,
            "checado_1": ["08:00:00", None, "08:30:00"],
            "hora_entrada_programada": ["08:00", "08:00", None],
            "cruza_medianoche": [False, False, False]
        })

        df_analizado = analizar_asistencia_con_horarios_cache(df_nulos, cache_horarios_especifico)

        # Verificar que se procesó correctamente
        assert not df_analizado.empty
        assert len(df_analizado) == len(df_nulos)

        # Verificar que se manejaron los casos nulos
        tipos_retardo = df_analizado["tipo_retardo"].tolist()
        assert "Falta" in tipos_retardo  # EMP002 sin checada
        assert "Día no Laborable" in tipos_retardo  # EMP003 sin horario

    def test_process_checkins_to_dataframe_fechas_extremas(self):
        """Prueba el procesamiento con fechas extremas."""
        # Datos con fechas muy separadas
        datos_fechas_extremas = [
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-01 08:00:00"},
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-31 17:00:00"}
        ]

        df = process_checkins_to_dataframe(datos_fechas_extremas, "2025-01-01", "2025-01-31")
        
        # Verificar que se procesó correctamente
        assert not df.empty
        
        # Verificar que se crearon filas para todos los días del rango
        assert len(df) > 30  # Al menos 31 días

    def test_analizar_asistencia_multiples_empleados_mismo_horario(self):
        """Prueba el análisis con múltiples empleados con el mismo horario."""
        df_multiples = pd.DataFrame({
            "employee": ["EMP001", "EMP002", "EMP003", "EMP004", "EMP005"],
            "dia": [date(2025, 1, 15)] * 5,
            "dia_iso": [3] * 5,
            "checado_1": ["08:00:00", "08:15:00", "08:30:00", "09:00:00", "10:00:00"],
            "hora_entrada_programada": ["08:00"] * 5,
            "cruza_medianoche": [False] * 5
        })

        cache_multiples = {
            "EMP001": {3: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0}},
            "EMP002": {3: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0}},
            "EMP003": {3: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0}},
            "EMP004": {3: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0}},
            "EMP005": {3: {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0}}
        }

        df_analizado = analizar_asistencia_con_horarios_cache(df_multiples, cache_multiples)

        # Verificar que se procesaron todos los empleados
        assert len(df_analizado) == 5
        
        # Verificar que se calcularon diferentes tipos de retardo
        tipos_retardo = df_analizado["tipo_retardo"].tolist()
        assert "A Tiempo" in tipos_retardo
        assert "Retardo" in tipos_retardo
        assert "Falta Injustificada" in tipos_retardo


class TestValidacionesEspecificas:
    """Pruebas para validaciones específicas del sistema."""

    @pytest.fixture
    def cache_horarios(self):
        """Fixture con caché de horarios para validaciones."""
        return {
            "EMP001": {
                "3": {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False, "horas_totales": 9.0}
            }
        }

    @pytest.mark.parametrize("checada,hora_prog,esperado", [
        ("08:00:00", "08:00", 0),
        ("8:0:0", "08:00", 0),  # Formato válido (se puede parsear)
        ("08:00", "8:0", float('inf')),    # Formato inválido
        ("25:00:00", "08:00", float('inf')),  # Hora inválida
        ("08:60:00", "08:00", float('inf')),  # Minuto inválido
    ])
    def test_validacion_formato_horas(self, checada, hora_prog, esperado):
        """Prueba la validación del formato de horas."""
        resultado = calcular_proximidad_horario(checada, hora_prog)
        assert resultado == esperado

    def test_validacion_rangos_fecha(self):
        """Prueba la validación de rangos de fecha."""
        # Rango válido
        datos_validos = [
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 08:00:00"}
        ]
        
        df_valido = process_checkins_to_dataframe(datos_validos, "2025-01-15", "2025-01-15")
        assert not df_valido.empty

        # Rango inválido (fecha final antes que inicial)
        df_invalido = process_checkins_to_dataframe(datos_validos, "2025-01-16", "2025-01-15")
        # Debería manejar el caso graciosamente
        assert isinstance(df_invalido, pd.DataFrame)

    def test_validacion_datos_duplicados(self):
        """Prueba la validación con datos duplicados."""
        datos_duplicados = [
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 08:00:00"},
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 08:00:00"},  # Duplicado
            {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 17:00:00"}
        ]

        df = process_checkins_to_dataframe(datos_duplicados, "2025-01-15", "2025-01-15")
        
        # Verificar que se procesó correctamente
        assert not df.empty
        
        # Verificar que las horas trabajadas se calcularon correctamente
        horas_trabajadas = df["horas_trabajadas"].iloc[0]
        assert horas_trabajadas != "00:00:00"

    def test_validacion_caracteres_especiales(self):
        """Prueba la validación con caracteres especiales en nombres."""
        datos_especiales = [
            {"employee": "EMP001", "employee_name": "Juan Pérez-García", "time": "2025-01-15 08:00:00"},
            {"employee": "EMP002", "employee_name": "María José O'Connor", "time": "2025-01-15 08:30:00"},
            {"employee": "EMP003", "employee_name": "José María López-Vega", "time": "2025-01-15 09:00:00"}
        ]

        df = process_checkins_to_dataframe(datos_especiales, "2025-01-15", "2025-01-15")
        
        # Verificar que se procesó correctamente
        assert not df.empty
        
        # Verificar que los nombres se mantuvieron
        nombres = df["Nombre"].tolist()
        assert "Juan Pérez-García" in nombres
        assert "María José O'Connor" in nombres
        assert "José María López-Vega" in nombres 