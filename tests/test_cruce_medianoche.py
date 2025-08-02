"""
Tests para el procesamiento de turnos que cruzan la medianoche.

Este módulo contiene tests que verifican:
1. Reorganización de checadas en turnos nocturnos
2. Cálculo correcto de horas trabajadas
3. Limpieza de check-outs del día siguiente
"""

import pytest
import pandas as pd
from datetime import datetime, date, timedelta
from generar_reporte_optimizado import procesar_horarios_con_medianoche


class TestCruceMedianoche:
    """Tests para el procesamiento de turnos que cruzan la medianoche."""

    @pytest.fixture
    def cache_horarios_nocturno(self):
        """Fixture con caché de horarios para turnos nocturnos."""
        return {
            "EMP001": {
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

    def test_cruce_medianoche_basico(self, cache_horarios_nocturno):
        """Prueba el caso básico de cruce de medianoche."""
        # Crear DataFrame con checadas que cruzan medianoche
        df = pd.DataFrame({
            'employee': ['EMP001', 'EMP001'],
            'dia': [date(2025, 7, 15), date(2025, 7, 16)],
            'dia_iso': [2, 3],  # Martes y Miércoles
            'es_primera_quincena': [True, True],
            'checado_1': ['23:10:00', '01:05:00'],
            'checado_2': ['23:15:00', '01:10:00'],
            'checado_3': ['23:20:00', '01:15:00'],
            'checado_4': ['23:25:00', '01:20:00'],
            'checado_5': ['23:30:00', '01:25:00'],
            'checado_6': ['23:35:00', '01:30:00'],
            'checado_7': ['23:40:00', '01:35:00'],
            'checado_8': ['23:45:00', '01:40:00'],
            'checado_9': ['23:50:00', '01:45:00'],
            'horas_trabajadas': ['00:00:00', '00:00:00'],
        })

        resultado = procesar_horarios_con_medianoche(df, cache_horarios_nocturno)

        # Verificar que se reorganizaron las checadas
        fila_dia_1 = resultado[resultado['dia'] == date(2025, 7, 15)].iloc[0]
        fila_dia_2 = resultado[resultado['dia'] == date(2025, 7, 16)].iloc[0]

        # El día 1 debe tener la entrada más temprana y la salida más tardía
        assert fila_dia_1['checado_1'] == '23:10:00'  # Entrada más temprana
        assert fila_dia_1['checado_2'] == '01:45:00'  # Salida más tardía del día siguiente

        # El día 2 debe tener las checadas restantes
        assert fila_dia_2['checado_1'] == '01:05:00'  # Primera checada del día siguiente
        assert fila_dia_2['checado_2'] == '01:10:00'  # Segunda checada del día siguiente

        # Verificar que se calculó correctamente las horas trabajadas
        assert fila_dia_1['horas_trabajadas'] == '02:35:00'  # 23:10 a 01:45

    def test_cruce_medianoche_solo_entrada_salida(self, cache_horarios_nocturno):
        """Prueba el caso donde solo hay entrada y salida."""
        df = pd.DataFrame({
            'employee': ['EMP001', 'EMP001'],
            'dia': [date(2025, 7, 15), date(2025, 7, 16)],
            'dia_iso': [2, 3],
            'es_primera_quincena': [True, True],
            'checado_1': ['23:10:00', '01:05:00'],
            'checado_2': [None, None],
            'checado_3': [None, None],
            'checado_4': [None, None],
            'checado_5': [None, None],
            'checado_6': [None, None],
            'checado_7': [None, None],
            'checado_8': [None, None],
            'checado_9': [None, None],
            'horas_trabajadas': ['00:00:00', '00:00:00'],
        })

        resultado = procesar_horarios_con_medianoche(df, cache_horarios_nocturno)

        fila_dia_1 = resultado[resultado['dia'] == date(2025, 7, 15)].iloc[0]
        fila_dia_2 = resultado[resultado['dia'] == date(2025, 7, 16)].iloc[0]

        # Debe reorganizar las checadas
        assert fila_dia_1['checado_1'] == '23:10:00'
        assert fila_dia_1['checado_2'] == '01:05:00'

        # El día siguiente debe quedar sin checadas principales
        assert pd.isna(fila_dia_2['checado_1'])
        assert pd.isna(fila_dia_2['checado_2'])

        # Verificar cálculo de horas
        assert fila_dia_1['horas_trabajadas'] == '01:55:00'  # 23:10 a 01:05

    def test_cruce_medianoche_sin_dia_siguiente(self, cache_horarios_nocturno):
        """Prueba el caso donde no hay día siguiente (último día del periodo)."""
        df = pd.DataFrame({
            'employee': ['EMP001'],
            'dia': [date(2025, 7, 31)],  # Último día del mes
            'dia_iso': [4],  # Jueves
            'es_primera_quincena': [False],
            'checado_1': ['23:10:00'],
            'checado_2': ['23:15:00'],
            'checado_3': ['23:20:00'],
            'checado_4': ['23:25:00'],
            'checado_5': ['23:30:00'],
            'checado_6': ['23:35:00'],
            'checado_7': ['23:40:00'],
            'checado_8': ['23:45:00'],
            'checado_9': ['23:50:00'],
            'horas_trabajadas': ['00:00:00'],
        })

        resultado = procesar_horarios_con_medianoche(df, cache_horarios_nocturno)

        # No debe haber cambios porque no hay día siguiente
        fila = resultado.iloc[0]
        assert fila['checado_1'] == '23:10:00'
        assert fila['checado_9'] == '23:50:00'
        # Las horas trabajadas pueden no calcularse correctamente sin día siguiente
        # pero las checadas deben mantenerse intactas

    def test_cruce_medianoche_multiples_empleados(self, cache_horarios_nocturno):
        """Prueba el cruce de medianoche con múltiples empleados."""
        # Agregar otro empleado al caché
        cache_horarios_nocturno["EMP002"] = cache_horarios_nocturno["EMP001"].copy()

        df = pd.DataFrame({
            'employee': ['EMP001', 'EMP001', 'EMP002', 'EMP002'],
            'dia': [date(2025, 7, 15), date(2025, 7, 16), date(2025, 7, 15), date(2025, 7, 16)],
            'dia_iso': [2, 3, 2, 3],
            'es_primera_quincena': [True, True, True, True],
            'checado_1': ['23:10:00', '01:05:00', '23:20:00', '01:15:00'],
            'checado_2': ['23:15:00', '01:10:00', '23:25:00', '01:20:00'],
            'checado_3': [None, None, None, None],
            'checado_4': [None, None, None, None],
            'checado_5': [None, None, None, None],
            'checado_6': [None, None, None, None],
            'checado_7': [None, None, None, None],
            'checado_8': [None, None, None, None],
            'checado_9': [None, None, None, None],
            'horas_trabajadas': ['00:00:00', '00:00:00', '00:00:00', '00:00:00'],
        })

        resultado = procesar_horarios_con_medianoche(df, cache_horarios_nocturno)

        # Verificar EMP001
        emp1_dia1 = resultado[(resultado['employee'] == 'EMP001') & (resultado['dia'] == date(2025, 7, 15))].iloc[0]
        emp1_dia2 = resultado[(resultado['employee'] == 'EMP001') & (resultado['dia'] == date(2025, 7, 16))].iloc[0]

        assert emp1_dia1['checado_1'] == '23:10:00'
        assert emp1_dia1['checado_2'] == '01:10:00'

        # Verificar EMP002
        emp2_dia1 = resultado[(resultado['employee'] == 'EMP002') & (resultado['dia'] == date(2025, 7, 15))].iloc[0]
        emp2_dia2 = resultado[(resultado['employee'] == 'EMP002') & (resultado['dia'] == date(2025, 7, 16))].iloc[0]

        assert emp2_dia1['checado_1'] == '23:20:00'
        assert emp2_dia1['checado_2'] == '01:20:00'

    def test_cruce_medianoche_sin_horario_nocturno(self):
        """Prueba que no se procese si no hay horario nocturno."""
        cache_horarios_normal = {
            "EMP001": {
                1: {
                    "hora_entrada": "08:00",
                    "hora_salida": "17:00",
                    "cruza_medianoche": False,
                    "horas_totales": 9.0,
                }
            }
        }

        df = pd.DataFrame({
            'employee': ['EMP001', 'EMP001'],
            'dia': [date(2025, 7, 15), date(2025, 7, 16)],
            'dia_iso': [2, 3],
            'es_primera_quincena': [True, True],
            'checado_1': ['23:10:00', '01:05:00'],
            'checado_2': ['23:15:00', '01:10:00'],
            'horas_trabajadas': ['00:00:00', '00:00:00'],
        })

        resultado = procesar_horarios_con_medianoche(df, cache_horarios_normal)

        # No debe haber cambios porque no es horario nocturno
        fila_dia1 = resultado[resultado['dia'] == date(2025, 7, 15)].iloc[0]
        fila_dia2 = resultado[resultado['dia'] == date(2025, 7, 16)].iloc[0]

        assert fila_dia1['checado_1'] == '23:10:00'
        assert fila_dia2['checado_1'] == '01:05:00'

    def test_cruce_medianoche_calculo_horas_preciso(self, cache_horarios_nocturno):
        """Prueba el cálculo preciso de horas trabajadas en cruce de medianoche."""
        df = pd.DataFrame({
            'employee': ['EMP001', 'EMP001'],
            'dia': [date(2025, 7, 15), date(2025, 7, 16)],
            'dia_iso': [2, 3],
            'es_primera_quincena': [True, True],
            'checado_1': ['23:00:00', '07:00:00'],  # Entrada exacta y salida exacta
            'checado_2': [None, None],
            'checado_3': [None, None],
            'checado_4': [None, None],
            'checado_5': [None, None],
            'checado_6': [None, None],
            'checado_7': [None, None],
            'checado_8': [None, None],
            'checado_9': [None, None],
            'horas_trabajadas': ['00:00:00', '00:00:00'],
        })

        resultado = procesar_horarios_con_medianoche(df, cache_horarios_nocturno)

        fila_dia1 = resultado[resultado['dia'] == date(2025, 7, 15)].iloc[0]
        
        # Debe calcular 8 horas exactas (23:00 a 07:00)
        assert fila_dia1['horas_trabajadas'] == '08:00:00' 