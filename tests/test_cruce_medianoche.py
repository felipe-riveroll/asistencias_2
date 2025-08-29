"""
Tests para el procesamiento de turnos que cruzan la medianoche.

Este módulo contiene tests que verifican:
1. Reorganización de checadas en turnos nocturnos
2. Cálculo correcto de horas trabajadas
3. Limpieza de check-outs del día siguiente
4. Funcionamiento de la ventana de gracia para marcas tardías
"""

import pytest
import pandas as pd
from datetime import datetime, date, timedelta
from data_processor import AttendanceProcessor


class TestCruceMedianoche:
    """Tests para el procesamiento de turnos que cruzan la medianoche."""

    @pytest.fixture
    def processor(self):
        """Fixture con el procesador de asistencia."""
        return AttendanceProcessor()

    @pytest.fixture
    def cache_horarios_nocturno(self):
        """Fixture con caché de horarios para turnos nocturnos."""
        return {
            "EMP001": {
                True: {  # Primera quincena
                    1: {
                        "hora_entrada": "23:00",
                        "hora_salida": "07:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    2: {
                        "hora_entrada": "23:00",
                        "hora_salida": "07:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    3: {
                        "hora_entrada": "23:00",
                        "hora_salida": "07:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    4: {
                        "hora_entrada": "23:00",
                        "hora_salida": "07:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    5: {
                        "hora_entrada": "23:00",
                        "hora_salida": "07:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    6: {
                        "hora_entrada": "23:00",
                        "hora_salida": "07:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    7: {
                        "hora_entrada": "23:00",
                        "hora_salida": "07:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                }
            }
        }

    def test_cruce_medianoche_basico(self, processor, cache_horarios_nocturno):
        """Prueba el caso básico de cruce de medianoche."""
        # Crear DataFrame con checadas que cruzan medianoche
        df = pd.DataFrame(
            {
                "employee": ["EMP001", "EMP001"],
                "dia": [date(2025, 7, 15), date(2025, 7, 16)],
                "dia_iso": [2, 3],  # Martes y Miércoles
                "es_primera_quincena": [True, True],
                "checado_1": ["23:10:00", "01:05:00"],
                "checado_2": ["23:15:00", "01:10:00"],
                "checado_3": ["23:20:00", "01:15:00"],
                "checado_4": ["23:25:00", "01:20:00"],
                "checado_5": ["23:30:00", "01:25:00"],
                "checado_6": ["23:35:00", "01:30:00"],
                "checado_7": ["23:40:00", "01:35:00"],
                "checado_8": ["23:45:00", "01:40:00"],
                "checado_9": ["23:50:00", "01:45:00"],
                "horas_trabajadas": ["00:00:00", "00:00:00"],
            }
        )

        resultado = processor.procesar_horarios_con_medianoche(
            df, cache_horarios_nocturno
        )

        # Verificar que se reorganizaron las checadas
        fila_dia_1 = resultado[resultado["dia"] == date(2025, 7, 15)].iloc[0]
        fila_dia_2 = resultado[resultado["dia"] == date(2025, 7, 16)].iloc[0]

        # El día 1 debe tener la entrada más temprana y la salida más tardía
        assert fila_dia_1["checado_1"] == "23:10:00"  # Entrada más temprana
        assert (
            fila_dia_1["checado_2"] == "01:45:00"
        )  # Salida más tardía del día siguiente

        # El día 2 debe tener las checadas restantes
        assert (
            fila_dia_2["checado_1"] == "01:05:00"
        )  # Primera checada del día siguiente
        assert (
            fila_dia_2["checado_2"] == "01:10:00"
        )  # Segunda checada del día siguiente

        # Verificar que se calculó correctamente las horas trabajadas
        assert fila_dia_1["horas_trabajadas"] == "02:35:00"  # 23:10 a 01:45

    def test_cruce_medianoche_solo_entrada_salida(
        self, processor, cache_horarios_nocturno
    ):
        """Prueba el caso donde solo hay entrada y salida."""
        df = pd.DataFrame(
            {
                "employee": ["EMP001", "EMP001"],
                "dia": [date(2025, 7, 15), date(2025, 7, 16)],
                "dia_iso": [2, 3],
                "es_primera_quincena": [True, True],
                "checado_1": ["23:10:00", "01:05:00"],
                "checado_2": [None, None],
                "checado_3": [None, None],
                "checado_4": [None, None],
                "checado_5": [None, None],
                "checado_6": [None, None],
                "checado_7": [None, None],
                "checado_8": [None, None],
                "checado_9": [None, None],
                "horas_trabajadas": ["00:00:00", "00:00:00"],
            }
        )

        resultado = processor.procesar_horarios_con_medianoche(
            df, cache_horarios_nocturno
        )

        fila_dia_1 = resultado[resultado["dia"] == date(2025, 7, 15)].iloc[0]
        fila_dia_2 = resultado[resultado["dia"] == date(2025, 7, 16)].iloc[0]

        # Debe reorganizar las checadas
        assert fila_dia_1["checado_1"] == "23:10:00"
        assert fila_dia_1["checado_2"] == "01:05:00"

        # El día siguiente debe quedar sin checadas principales
        assert pd.isna(fila_dia_2["checado_1"])
        assert pd.isna(fila_dia_2["checado_2"])

        # Verificar cálculo de horas
        assert fila_dia_1["horas_trabajadas"] == "01:55:00"  # 23:10 a 01:05

    def test_cruce_medianoche_sin_dia_siguiente(
        self, processor, cache_horarios_nocturno
    ):
        """Prueba el caso donde no hay día siguiente (último día del periodo)."""
        df = pd.DataFrame(
            {
                "employee": ["EMP001"],
                "dia": [date(2025, 7, 31)],  # Último día del mes
                "dia_iso": [4],  # Jueves
                "es_primera_quincena": [False],
                "checado_1": ["23:10:00"],
                "checado_2": ["23:15:00"],
                "checado_3": ["23:20:00"],
                "checado_4": ["23:25:00"],
                "checado_5": ["23:30:00"],
                "checado_6": ["23:35:00"],
                "checado_7": ["23:40:00"],
                "checado_8": ["23:45:00"],
                "checado_9": ["23:50:00"],
                "horas_trabajadas": ["00:00:00"],
            }
        )

        resultado = processor.procesar_horarios_con_medianoche(
            df, cache_horarios_nocturno
        )

        # No debe haber cambios porque no hay día siguiente
        fila = resultado.iloc[0]
        assert fila["checado_1"] == "23:10:00"
        assert fila["checado_9"] == "23:50:00"
        # Las horas trabajadas pueden no calcularse correctamente sin día siguiente
        # pero las checadas deben mantenerse intactas

    def test_cruce_medianoche_multiples_empleados(
        self, processor, cache_horarios_nocturno
    ):
        """Prueba el cruce de medianoche con múltiples empleados."""
        # Agregar otro empleado al caché
        cache_horarios_nocturno["EMP002"] = cache_horarios_nocturno["EMP001"].copy()

        df = pd.DataFrame(
            {
                "employee": ["EMP001", "EMP001", "EMP002", "EMP002"],
                "dia": [
                    date(2025, 7, 15),
                    date(2025, 7, 16),
                    date(2025, 7, 15),
                    date(2025, 7, 16),
                ],
                "dia_iso": [2, 3, 2, 3],
                "es_primera_quincena": [True, True, True, True],
                "checado_1": ["23:10:00", "01:05:00", "23:20:00", "01:15:00"],
                "checado_2": ["23:15:00", "01:10:00", "23:25:00", "01:20:00"],
                "checado_3": [None, None, None, None],
                "checado_4": [None, None, None, None],
                "checado_5": [None, None, None, None],
                "checado_6": [None, None, None, None],
                "checado_7": [None, None, None, None],
                "checado_8": [None, None, None, None],
                "checado_9": [None, None, None, None],
                "horas_trabajadas": ["00:00:00", "00:00:00", "00:00:00", "00:00:00"],
            }
        )

        resultado = processor.procesar_horarios_con_medianoche(
            df, cache_horarios_nocturno
        )

        # Verificar EMP001
        emp1_dia1 = resultado[
            (resultado["employee"] == "EMP001")
            & (resultado["dia"] == date(2025, 7, 15))
        ].iloc[0]
        emp1_dia2 = resultado[
            (resultado["employee"] == "EMP001")
            & (resultado["dia"] == date(2025, 7, 16))
        ].iloc[0]

        assert emp1_dia1["checado_1"] == "23:10:00"
        assert emp1_dia1["checado_2"] == "01:10:00"

        # Verificar EMP002
        emp2_dia1 = resultado[
            (resultado["employee"] == "EMP002")
            & (resultado["dia"] == date(2025, 7, 15))
        ].iloc[0]
        emp2_dia2 = resultado[
            (resultado["employee"] == "EMP002")
            & (resultado["dia"] == date(2025, 7, 16))
        ].iloc[0]

        assert emp2_dia1["checado_1"] == "23:20:00"
        assert emp2_dia1["checado_2"] == "01:20:00"

    def test_cruce_medianoche_sin_horario_nocturno(self, processor):
        """Prueba que no se procese si no hay horario nocturno."""
        cache_horarios_normal = {
            "EMP001": {
                True: {  # Primera quincena
                    1: {
                        "hora_entrada": "08:00",
                        "hora_salida": "17:00",
                        "cruza_medianoche": False,
                        "horas_totales": 9.0,
                    },
                    2: {
                        "hora_entrada": "08:00",
                        "hora_salida": "17:00",
                        "cruza_medianoche": False,
                        "horas_totales": 9.0,
                    },
                    3: {
                        "hora_entrada": "08:00",
                        "hora_salida": "17:00",
                        "cruza_medianoche": False,
                        "horas_totales": 9.0,
                    },
                    4: {
                        "hora_entrada": "08:00",
                        "hora_salida": "17:00",
                        "cruza_medianoche": False,
                        "horas_totales": 9.0,
                    },
                    5: {
                        "hora_entrada": "08:00",
                        "hora_salida": "17:00",
                        "cruza_medianoche": False,
                        "horas_totales": 9.0,
                    },
                    6: {
                        "hora_entrada": "08:00",
                        "hora_salida": "17:00",
                        "cruza_medianoche": False,
                        "horas_totales": 9.0,
                    },
                    7: {
                        "hora_entrada": "08:00",
                        "hora_salida": "17:00",
                        "cruza_medianoche": False,
                        "horas_totales": 9.0,
                    },
                }
            }
        }

        df = pd.DataFrame(
            {
                "employee": ["EMP001", "EMP001"],
                "dia": [date(2025, 7, 15), date(2025, 7, 16)],
                "dia_iso": [2, 3],
                "es_primera_quincena": [True, True],
                "checado_1": ["23:10:00", "01:05:00"],
                "checado_2": ["23:15:00", "01:10:00"],
                "horas_trabajadas": ["00:00:00", "00:00:00"],
            }
        )

        resultado = processor.procesar_horarios_con_medianoche(
            df, cache_horarios_normal
        )

        # No debe haber cambios porque no es horario nocturno
        fila_dia1 = resultado[resultado["dia"] == date(2025, 7, 15)].iloc[0]
        fila_dia2 = resultado[resultado["dia"] == date(2025, 7, 16)].iloc[0]

        assert fila_dia1["checado_1"] == "23:10:00"
        assert fila_dia2["checado_1"] == "01:05:00"

    def test_cruce_medianoche_calculo_horas_preciso(
        self, processor, cache_horarios_nocturno
    ):
        """Prueba el cálculo preciso de horas trabajadas en cruce de medianoche."""
        df = pd.DataFrame(
            {
                "employee": ["EMP001", "EMP001"],
                "dia": [date(2025, 7, 15), date(2025, 7, 16)],
                "dia_iso": [2, 3],
                "es_primera_quincena": [True, True],
                "checado_1": ["23:00:00", "07:00:00"],  # Entrada exacta y salida exacta
                "checado_2": [None, None],
                "checado_3": [None, None],
                "checado_4": [None, None],
                "checado_5": [None, None],
                "checado_6": [None, None],
                "checado_7": [None, None],
                "checado_8": [None, None],
                "checado_9": [None, None],
                "horas_trabajadas": ["00:00:00", "00:00:00"],
            }
        )

        resultado = processor.procesar_horarios_con_medianoche(
            df, cache_horarios_nocturno
        )

        fila_dia1 = resultado[resultado["dia"] == date(2025, 7, 15)].iloc[0]

        # Debe calcular 8 horas exactas (23:00 a 07:00)
        assert fila_dia1["horas_trabajadas"] == "08:00:00"

    def test_ventana_gracia_marcas_tardias(self, processor):
        """
        Prueba específica para la ventana de gracia con marcas tardías.

        Caso de prueba: Turno 18:00 → 02:00 con marcas a las 02:05, 02:07
        Esperado: Todas las marcas deben pertenecer al turno del día anterior
        """
        # Cache con horario que cruza medianoche (18:00 → 02:00) - formato multi-quincena
        cache_horarios = {
            "EMP001": {
                True: {  # Primera quincena
                    1: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    2: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    3: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    4: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    5: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    6: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    7: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                }
            }
        }

        # DataFrame con marcas: entrada 18:04, salidas tardías 02:05, 02:07
        df = pd.DataFrame(
            {
                "employee": ["EMP001", "EMP001"],
                "dia": [date(2025, 7, 3), date(2025, 7, 4)],  # Jueves y Viernes
                "dia_iso": [4, 5],
                "es_primera_quincena": [True, True],
                "checado_1": ["18:04:00", "02:05:00"],  # Entrada y primera marca tardía
                "checado_2": [None, "02:07:00"],  # Segunda marca tardía
                "checado_3": [None, None],
                "checado_4": [None, None],
                "checado_5": [None, None],
                "checado_6": [None, None],
                "checado_7": [None, None],
                "checado_8": [None, None],
                "checado_9": [None, None],
                "horas_trabajadas": ["00:00:00", "00:00:00"],
            }
        )

        resultado = processor.procesar_horarios_con_medianoche(df, cache_horarios)

        # Verificar que todas las marcas se asignaron al turno del día anterior (3 de julio)
        fila_turno = resultado[resultado["dia"] == date(2025, 7, 3)].iloc[0]
        fila_siguiente = resultado[resultado["dia"] == date(2025, 7, 4)].iloc[0]

        # El turno del 3 de julio debe tener entrada=18:04 y salida=02:07
        assert fila_turno["checado_1"] == "18:04:00"  # Entrada original
        assert fila_turno["checado_2"] == "02:07:00"  # Última marca tardía

        # El día siguiente (4 de julio) no debe tener marcas asignadas
        assert pd.isna(fila_siguiente["checado_1"])
        assert pd.isna(fila_siguiente["checado_2"])

        # Verificar que las horas trabajadas se calcularon correctamente
        # 18:04 a 02:07 del día siguiente = aproximadamente 8 horas
        horas_trabajadas = fila_turno["horas_trabajadas"]
        assert horas_trabajadas is not None
        assert horas_trabajadas != "00:00:00"

    def test_ventana_gracia_limite_exacto(self, processor):
        """
        Prueba el límite exacto de la ventana de gracia (GRACE_MINUTES = 59).

        Caso: Turno 18:00 → 02:00
        - Marca a las 02:59:59 → debe pertenecer al turno anterior
        - Marca a las 03:00:00 → debe pertenecer al turno siguiente
        """
        cache_horarios = {
            "EMP001": {
                True: {  # Primera quincena
                    1: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    2: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    3: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    4: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    5: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    6: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    7: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                }
            }
        }

        # DataFrame con marcas en el límite de la ventana de gracia
        df = pd.DataFrame(
            {
                "employee": ["EMP001", "EMP001", "EMP001"],
                "dia": [date(2025, 7, 3), date(2025, 7, 4), date(2025, 7, 4)],
                "dia_iso": [4, 5, 5],
                "es_primera_quincena": [True, True, True],
                "checado_1": [
                    "18:00:00",
                    "02:59:59",
                    "03:00:00",
                ],  # Límite y después del límite
                "checado_2": [None, None, None],
                "checado_3": [None, None, None],
                "checado_4": [None, None, None],
                "checado_5": [None, None, None],
                "checado_6": [None, None, None],
                "checado_7": [None, None, None],
                "checado_8": [None, None, None],
                "checado_9": [None, None, None],
                "horas_trabajadas": ["00:00:00", "00:00:00", "00:00:00"],
            }
        )

        resultado = processor.procesar_horarios_con_medianoche(df, cache_horarios)

        # La marca 02:59:59 debe pertenecer al turno del 3 de julio
        fila_turno = resultado[resultado["dia"] == date(2025, 7, 3)].iloc[0]
        assert fila_turno["checado_1"] == "18:00:00"
        assert fila_turno["checado_2"] == "02:59:59"

        # La marca 03:00:00 debe permanecer en el 4 de julio
        fila_siguiente = resultado[resultado["dia"] == date(2025, 7, 4)].iloc[0]
        assert fila_siguiente["checado_1"] == "03:00:00"

    def test_only_checkout_nocturno(self, processor):
        """
        Prueba específica para turno nocturno con solo salida (sin entrada).

        Caso de prueba: Turno 18:00 → 02:00 con solo marcas a las 02:05, 02:07
        Esperado: entrada=None, salida=02:07, shift_date=2025-07-19, observaciones="Falta registro de entrada"
        """
        # Cache con horario que cruza medianoche (18:00 → 02:00)
        cache_horarios = {
            "EMP001": {
                True: {  # Primera quincena
                    1: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    2: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    3: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    4: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    5: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    6: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                    7: {
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00",
                        "cruza_medianoche": True,
                        "horas_totales": 8.0,
                    },
                }
            }
        }

        # DataFrame con solo marcas de salida tardías (02:05, 02:07)
        df = pd.DataFrame(
            {
                "employee": ["EMP001"],
                "dia": [date(2025, 7, 20)],  # Domingo
                "dia_iso": [7],
                "es_primera_quincena": [True],
                "checado_1": ["02:05:00"],  # Solo marca tardía
                "checado_2": ["02:07:00"],  # Segunda marca tardía
                "checado_3": [None],
                "checado_4": [None],
                "checado_5": [None],
                "checado_6": [None],
                "checado_7": [None],
                "checado_8": [None],
                "checado_9": [None],
                "horas_trabajadas": ["00:00:00"],
            }
        )

        resultado = processor.procesar_horarios_con_medianoche(df, cache_horarios)

        # Verificar que se asignó al turno del día anterior (19 de julio)
        fila_turno = resultado[resultado["dia"] == date(2025, 7, 19)].iloc[0]

        # La entrada debe estar vacía (None)
        assert pd.isna(fila_turno["checado_1"])

        # La salida debe ser la última marca tardía
        assert fila_turno["checado_2"] == "02:07:00"

        # Las horas trabajadas deben ser 0
        assert fila_turno["horas_trabajadas"] == "00:00:00"

        # Debe tener la observación de entrada faltante
        assert "observaciones" in fila_turno
        assert "Falta registro de entrada" in str(fila_turno["observaciones"])

        # El día original (20 de julio) debe estar limpio
        fila_original = resultado[resultado["dia"] == date(2025, 7, 20)]
        if not fila_original.empty:
            fila_original = fila_original.iloc[0]
            assert pd.isna(fila_original["checado_1"])
            assert pd.isna(fila_original["checado_2"])
