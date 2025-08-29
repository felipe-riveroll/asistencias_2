"""
Tests específicos para verificar el umbral de 60 minutos para "Falta Injustificada".
"""

import pytest
import pandas as pd
from datetime import date
from generar_reporte_optimizado import analizar_asistencia_con_horarios_cache


class TestUmbralFaltaInjustificada:
    """Tests para verificar el nuevo umbral de 60 minutos para 'Falta Injustificada'."""

    @pytest.fixture
    def cache_horarios_umbral(self):
        """Fixture con horarios para probar el umbral."""
        return {
            "EMP001": {
                3: {  # Miércoles
                    "hora_entrada": "08:00",
                    "hora_salida": "17:00",
                    "cruza_medianoche": False,
                    "horas_totales": 9.0,
                }
            }
        }

    @pytest.mark.parametrize(
        "checada,hora_prog,esperado,descripcion",
        [
            ("08:00:00", "08:00", "A Tiempo", "Llegada exacta"),
            ("08:15:00", "08:00", "A Tiempo", "Llegada dentro de tolerancia"),
            ("08:16:00", "08:00", "Retardo", "Llegada 16 min tarde"),
            ("08:30:00", "08:00", "Retardo", "Llegada 30 min tarde"),
            ("08:45:00", "08:00", "Retardo", "Llegada 45 min tarde"),
            ("09:00:00", "08:00", "Retardo", "Llegada 60 min tarde (límite)"),
            (
                "09:01:00",
                "08:00",
                "Falta Injustificada",
                "Llegada 61 min tarde (nuevo umbral)",
            ),
            ("09:30:00", "08:00", "Falta Injustificada", "Llegada 90 min tarde"),
            ("10:00:00", "08:00", "Falta Injustificada", "Llegada 2 horas tarde"),
        ],
    )
    def test_umbral_60_minutos_falta_injustificada(
        self, cache_horarios_umbral, checada, hora_prog, esperado, descripcion
    ):
        """Prueba el nuevo umbral de 60 minutos para 'Falta Injustificada'."""
        # Crear DataFrame con caso específico
        df_caso = pd.DataFrame(
            {
                "employee": ["EMP001"],
                "dia": [date(2025, 1, 15)],
                "dia_iso": [3],
                "checado_1": [checada],
                "hora_entrada_programada": [hora_prog],
                "cruza_medianoche": [False],
            }
        )

        # Analizar asistencia
        df_analizado = analizar_asistencia_con_horarios_cache(
            df_caso, cache_horarios_umbral
        )

        # Verificar el tipo de retardo
        tipo_retardo = df_analizado["tipo_retardo"].iloc[0]
        assert tipo_retardo == esperado, (
            f"Error en {descripcion}: esperado {esperado}, obtenido {tipo_retardo}"
        )

    def test_umbral_con_turno_nocturno(self):
        """Prueba el umbral en turnos nocturnos que cruzan medianoche."""
        cache_nocturno = {
            "EMP002": {
                3: {
                    "hora_entrada": "22:00",
                    "hora_salida": "06:00",
                    "cruza_medianoche": True,
                    "horas_totales": 8.0,
                }
            }
        }

        # Casos específicos para turno nocturno
        casos_nocturno = [
            ("22:00:00", "22:00", "A Tiempo", "Entrada exacta"),
            ("22:15:00", "22:00", "A Tiempo", "Entrada dentro de tolerancia"),
            ("22:16:00", "22:00", "Retardo", "Entrada 16 min tarde"),
            ("23:00:00", "22:00", "Retardo", "Entrada 60 min tarde (límite)"),
            (
                "23:01:00",
                "22:00",
                "Falta Injustificada",
                "Entrada 61 min tarde (nuevo umbral)",
            ),
            ("00:00:00", "22:00", "Falta Injustificada", "Entrada 2 horas tarde"),
        ]

        for checada, hora_prog, esperado, descripcion in casos_nocturno:
            df_caso = pd.DataFrame(
                {
                    "employee": ["EMP002"],
                    "dia": [date(2025, 1, 15)],
                    "dia_iso": [3],
                    "checado_1": [checada],
                    "hora_entrada_programada": [hora_prog],
                    "cruza_medianoche": [True],
                }
            )

            df_analizado = analizar_asistencia_con_horarios_cache(
                df_caso, cache_nocturno
            )

            tipo_retardo = df_analizado["tipo_retardo"].iloc[0]
            assert tipo_retardo == esperado, (
                f"Error en turno nocturno - {descripcion}: esperado {esperado}, obtenido {tipo_retardo}"
            )

    def test_umbral_con_llegadas_tempranas(self, cache_horarios_umbral):
        """Prueba que las llegadas tempranas se clasifiquen correctamente."""
        casos_tempranos = [
            ("07:45:00", "08:00", "A Tiempo", "Llegada 15 min temprana"),
            ("07:30:00", "08:00", "A Tiempo", "Llegada 30 min temprana"),
            ("07:00:00", "08:00", "A Tiempo", "Llegada 1 hora temprana"),
        ]

        for checada, hora_prog, esperado, descripcion in casos_tempranos:
            df_caso = pd.DataFrame(
                {
                    "employee": ["EMP001"],
                    "dia": [date(2025, 1, 15)],
                    "dia_iso": [3],
                    "checado_1": [checada],
                    "hora_entrada_programada": [hora_prog],
                    "cruza_medianoche": [False],
                }
            )

            df_analizado = analizar_asistencia_con_horarios_cache(
                df_caso, cache_horarios_umbral
            )

            tipo_retardo = df_analizado["tipo_retardo"].iloc[0]
            assert tipo_retardo == esperado, (
                f"Error en llegada temprana - {descripcion}: esperado {esperado}, obtenido {tipo_retardo}"
            )

    def test_umbral_con_diferentes_horarios(self):
        """Prueba el umbral con diferentes horarios de entrada."""
        cache_diferentes_horarios = {
            "EMP003": {
                3: {
                    "hora_entrada": "06:00",
                    "hora_salida": "14:00",
                    "cruza_medianoche": False,
                    "horas_totales": 8.0,
                }
            },
            "EMP004": {
                3: {
                    "hora_entrada": "14:00",
                    "hora_salida": "22:00",
                    "cruza_medianoche": False,
                    "horas_totales": 8.0,
                }
            },
        }

        # Casos para horario matutino (06:00)
        df_matutino = pd.DataFrame(
            {
                "employee": ["EMP003"],
                "dia": [date(2025, 1, 15)],
                "dia_iso": [3],
                "checado_1": ["07:01:00"],  # 61 min tarde
                "hora_entrada_programada": ["06:00"],
                "cruza_medianoche": [False],
            }
        )

        df_analizado_matutino = analizar_asistencia_con_horarios_cache(
            df_matutino, cache_diferentes_horarios
        )
        assert df_analizado_matutino["tipo_retardo"].iloc[0] == "Falta Injustificada"

        # Casos para horario vespertino (14:00)
        df_vespertino = pd.DataFrame(
            {
                "employee": ["EMP004"],
                "dia": [date(2025, 1, 15)],
                "dia_iso": [3],
                "checado_1": ["15:01:00"],  # 61 min tarde
                "hora_entrada_programada": ["14:00"],
                "cruza_medianoche": [False],
            }
        )

        df_analizado_vespertino = analizar_asistencia_con_horarios_cache(
            df_vespertino, cache_diferentes_horarios
        )
        assert df_analizado_vespertino["tipo_retardo"].iloc[0] == "Falta Injustificada"

    def test_umbral_con_faltas_sin_checada(self, cache_horarios_umbral):
        """Prueba que las faltas sin checada se clasifiquen correctamente."""
        df_sin_checada = pd.DataFrame(
            {
                "employee": ["EMP001"],
                "dia": [date(2025, 1, 15)],
                "dia_iso": [3],
                "checado_1": [None],  # Sin checada
                "hora_entrada_programada": ["08:00"],
                "cruza_medianoche": [False],
            }
        )

        df_analizado = analizar_asistencia_con_horarios_cache(
            df_sin_checada, cache_horarios_umbral
        )

        assert df_analizado["tipo_retardo"].iloc[0] == "Falta"

    def test_umbral_con_dia_no_laborable(self, cache_horarios_umbral):
        """Prueba que los días no laborables se clasifiquen correctamente."""
        df_no_laborable = pd.DataFrame(
            {
                "employee": ["EMP999"],  # Empleado que no existe en el caché
                "dia": [date(2025, 1, 15)],
                "dia_iso": [3],
                "checado_1": ["08:00:00"],
                "hora_entrada_programada": [None],  # Sin horario programado
                "cruza_medianoche": [False],
            }
        )

        df_analizado = analizar_asistencia_con_horarios_cache(
            df_no_laborable, cache_horarios_umbral
        )

        assert df_analizado["tipo_retardo"].iloc[0] == "Día no Laborable"
