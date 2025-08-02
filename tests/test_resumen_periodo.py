"""
Tests para el resumen del periodo.

Este módulo contiene tests que verifican:
1. Cálculo correcto de totales por empleado
2. Formateo de diferencia_HHMMSS con signo ± correcto
3. Manejo de permisos y descuentos
4. Casos edge y datos vacíos
"""

import pytest
import pandas as pd
from datetime import date, timedelta
from generar_reporte_optimizado import generar_resumen_periodo


class TestResumenPeriodo:
    """Tests para el resumen del periodo."""

    def test_resumen_periodo_basico(self):
        """Prueba el resumen básico del periodo."""
        df = pd.DataFrame({
            'employee': ['EMP001', 'EMP001', 'EMP002', 'EMP002'],
            'Nombre': ['Juan Pérez', 'Juan Pérez', 'María García', 'María García'],
            'dia': [date(2025, 7, 15), date(2025, 7, 16), date(2025, 7, 15), date(2025, 7, 16)],
            'horas_trabajadas': ['08:00:00', '07:30:00', '08:00:00', '08:00:00'],
            'horas_esperadas': ['08:00:00', '08:00:00', '08:00:00', '08:00:00'],
            'es_retardo_acumulable': [0, 1, 0, 0],
            'es_falta': [0, 0, 0, 0],
        })

        resultado = generar_resumen_periodo(df)

        assert len(resultado) == 2
        assert 'EMP001' in resultado['employee'].values
        assert 'EMP002' in resultado['employee'].values

        # Verificar totales de EMP001
        emp1 = resultado[resultado['employee'] == 'EMP001'].iloc[0]
        assert emp1['total_horas_trabajadas'] == '15:30:00'  # 8:00 + 7:30
        assert emp1['total_horas_esperadas'] == '16:00:00'   # 8:00 + 8:00
        assert emp1['total_retardos'] == 1
        assert emp1['faltas_del_periodo'] == 0

        # Verificar totales de EMP002
        emp2 = resultado[resultado['employee'] == 'EMP002'].iloc[0]
        assert emp2['total_horas_trabajadas'] == '16:00:00'  # 8:00 + 8:00
        assert emp2['total_horas_esperadas'] == '16:00:00'   # 8:00 + 8:00
        assert emp2['total_retardos'] == 0
        assert emp2['faltas_del_periodo'] == 0

    def test_resumen_periodo_con_permisos(self):
        """Prueba el resumen con permisos y descuentos."""
        df = pd.DataFrame({
            'employee': ['EMP001', 'EMP001', 'EMP002', 'EMP002'],
            'Nombre': ['Juan Pérez', 'Juan Pérez', 'María García', 'María García'],
            'dia': [date(2025, 7, 15), date(2025, 7, 16), date(2025, 7, 15), date(2025, 7, 16)],
            'horas_trabajadas': ['08:00:00', '00:00:00', '08:00:00', '08:00:00'],
            'horas_esperadas_originales': ['08:00:00', '08:00:00', '08:00:00', '08:00:00'],
            'horas_descontadas_permiso': ['00:00:00', '08:00:00', '00:00:00', '00:00:00'],
            'es_retardo_acumulable': [0, 0, 0, 0],
            'es_falta_ajustada': [0, 0, 0, 0],
            'es_falta': [0, 0, 0, 0],
            'falta_justificada': [0, 1, 0, 0],
        })

        resultado = generar_resumen_periodo(df)

        # Verificar EMP001 con permiso
        emp1 = resultado[resultado['employee'] == 'EMP001'].iloc[0]
        assert emp1['total_horas_trabajadas'] == '08:00:00'
        assert emp1['total_horas_esperadas'] == '16:00:00'
        assert emp1['total_horas_descontadas_permiso'] == '08:00:00'
        assert emp1['total_horas'] == '08:00:00'  # Esperadas - Descontadas
        assert emp1['faltas_justificadas'] == 1

        # Verificar EMP002 sin permiso
        emp2 = resultado[resultado['employee'] == 'EMP002'].iloc[0]
        assert emp2['total_horas_trabajadas'] == '16:00:00'
        assert emp2['total_horas_esperadas'] == '16:00:00'
        assert emp2['total_horas_descontadas_permiso'] == '00:00:00'
        assert emp2['total_horas'] == '16:00:00'

    def test_formato_diferencia_horas(self):
        """Prueba el formateo de diferencia_HHMMSS con signo ± correcto."""
        df = pd.DataFrame({
            'employee': ['EMP001', 'EMP001', 'EMP002', 'EMP002', 'EMP003', 'EMP003'],
            'Nombre': ['Juan', 'Juan', 'María', 'María', 'Pedro', 'Pedro'],
            'dia': [date(2025, 7, 15), date(2025, 7, 16), date(2025, 7, 15), date(2025, 7, 16), date(2025, 7, 15), date(2025, 7, 16)],
            'horas_trabajadas': ['09:00:00', '08:00:00', '07:00:00', '08:00:00', '08:00:00', '08:00:00'],
            'horas_esperadas_originales': ['08:00:00', '08:00:00', '08:00:00', '08:00:00', '08:00:00', '08:00:00'],
            'horas_descontadas_permiso': ['00:00:00', '00:00:00', '00:00:00', '00:00:00', '00:00:00', '00:00:00'],
            'es_retardo_acumulable': [0, 0, 0, 0, 0, 0],
            'es_falta_ajustada': [0, 0, 0, 0, 0, 0],
            'es_falta': [0, 0, 0, 0, 0, 0],
            'falta_justificada': [0, 0, 0, 0, 0, 0],
        })

        resultado = generar_resumen_periodo(df)

        # EMP001: trabajó más de lo esperado (+1 hora)
        emp1 = resultado[resultado['employee'] == 'EMP001'].iloc[0]
        assert emp1['diferencia_HHMMSS'] == '+01:00:00'

        # EMP002: trabajó menos de lo esperado (-1 hora)
        emp2 = resultado[resultado['employee'] == 'EMP002'].iloc[0]
        assert emp2['diferencia_HHMMSS'] == '-01:00:00'

        # EMP003: trabajó exactamente lo esperado
        emp3 = resultado[resultado['employee'] == 'EMP003'].iloc[0]
        assert emp3['diferencia_HHMMSS'] == '00:00:00'

    def test_resumen_periodo_datos_vacios(self):
        """Prueba el resumen con DataFrame vacío."""
        df = pd.DataFrame()
        resultado = generar_resumen_periodo(df)
        assert resultado.empty

    def test_resumen_periodo_columnas_opcionales(self):
        """Prueba el resumen cuando faltan columnas opcionales."""
        df = pd.DataFrame({
            'employee': ['EMP001', 'EMP001'],
            'Nombre': ['Juan Pérez', 'Juan Pérez'],
            'dia': [date(2025, 7, 15), date(2025, 7, 16)],
            'horas_trabajadas': ['08:00:00', '08:00:00'],
            'horas_esperadas': ['08:00:00', '08:00:00'],
            'es_retardo_acumulable': [0, 0],
            'es_falta_ajustada': [0, 0],
            'es_falta': [0, 0],
        })

        resultado = generar_resumen_periodo(df)

        assert len(resultado) == 1
        emp1 = resultado.iloc[0]
        assert emp1['total_horas_trabajadas'] == '16:00:00'
        assert emp1['total_horas_esperadas'] == '16:00:00'
        assert emp1['total_horas_descontadas_permiso'] == '00:00:00'
        assert emp1['total_horas'] == '16:00:00'
        assert emp1['faltas_justificadas'] == 0

    def test_resumen_periodo_con_faltas(self):
        """Prueba el resumen con faltas y retardos."""
        df = pd.DataFrame({
            'employee': ['EMP001', 'EMP001', 'EMP001', 'EMP002', 'EMP002'],
            'Nombre': ['Juan Pérez', 'Juan Pérez', 'Juan Pérez', 'María García', 'María García'],
            'dia': [date(2025, 7, 15), date(2025, 7, 16), date(2025, 7, 17), date(2025, 7, 15), date(2025, 7, 16)],
            'horas_trabajadas': ['08:00:00', '00:00:00', '08:00:00', '08:00:00', '00:00:00'],
            'horas_esperadas_originales': ['08:00:00', '08:00:00', '08:00:00', '08:00:00', '08:00:00'],
            'horas_descontadas_permiso': ['00:00:00', '00:00:00', '00:00:00', '00:00:00', '00:00:00'],
            'es_retardo_acumulable': [0, 0, 1, 0, 0],
            'es_falta_ajustada': [0, 1, 0, 0, 1],
            'es_falta': [0, 1, 0, 0, 1],
            'falta_justificada': [0, 0, 0, 0, 0],
        })

        resultado = generar_resumen_periodo(df)

        # Verificar EMP001
        emp1 = resultado[resultado['employee'] == 'EMP001'].iloc[0]
        assert emp1['total_retardos'] == 1
        assert emp1['faltas_del_periodo'] == 1
        assert emp1['faltas_justificadas'] == 0

        # Verificar EMP002
        emp2 = resultado[resultado['employee'] == 'EMP002'].iloc[0]
        assert emp2['total_retardos'] == 0
        assert emp2['faltas_del_periodo'] == 1
        assert emp2['faltas_justificadas'] == 0

    def test_resumen_periodo_diferencia_negativa(self):
        """Prueba el formateo de diferencia negativa."""
        df = pd.DataFrame({
            'employee': ['EMP001', 'EMP001'],
            'Nombre': ['Juan Pérez', 'Juan Pérez'],
            'dia': [date(2025, 7, 15), date(2025, 7, 16)],
            'horas_trabajadas': ['06:00:00', '07:00:00'],  # Menos horas trabajadas
            'horas_esperadas_originales': ['08:00:00', '08:00:00'],
            'horas_descontadas_permiso': ['00:00:00', '00:00:00'],
            'es_retardo_acumulable': [0, 0],
            'es_falta_ajustada': [0, 0],
            'es_falta': [0, 0],
            'falta_justificada': [0, 0],
        })

        resultado = generar_resumen_periodo(df)

        emp1 = resultado.iloc[0]
        assert emp1['diferencia_HHMMSS'] == '-03:00:00'  # 13 horas trabajadas vs 16 esperadas

    def test_resumen_periodo_diferencia_positiva(self):
        """Prueba el formateo de diferencia positiva."""
        df = pd.DataFrame({
            'employee': ['EMP001', 'EMP001'],
            'Nombre': ['Juan Pérez', 'Juan Pérez'],
            'dia': [date(2025, 7, 15), date(2025, 7, 16)],
            'horas_trabajadas': ['10:00:00', '09:00:00'],  # Más horas trabajadas
            'horas_esperadas_originales': ['08:00:00', '08:00:00'],
            'horas_descontadas_permiso': ['00:00:00', '00:00:00'],
            'es_retardo_acumulable': [0, 0],
            'es_falta_ajustada': [0, 0],
            'es_falta': [0, 0],
            'falta_justificada': [0, 0],
        })

        resultado = generar_resumen_periodo(df)

        emp1 = resultado.iloc[0]
        assert emp1['diferencia_HHMMSS'] == '+03:00:00'  # 19 horas trabajadas vs 16 esperadas

    def test_resumen_periodo_estructura_columnas(self):
        """Prueba que el resumen tenga la estructura de columnas correcta."""
        df = pd.DataFrame({
            'employee': ['EMP001'],
            'Nombre': ['Juan Pérez'],
            'dia': [date(2025, 7, 15)],
            'horas_trabajadas': ['08:00:00'],
            'horas_esperadas_originales': ['08:00:00'],
            'horas_descontadas_permiso': ['00:00:00'],
            'es_retardo_acumulable': [0],
            'es_falta_ajustada': [0],
            'es_falta': [0],
            'falta_justificada': [0],
        })

        resultado = generar_resumen_periodo(df)

        columnas_esperadas = [
            'employee', 'Nombre', 'total_horas_trabajadas', 'total_horas_esperadas',
            'total_horas_descontadas_permiso', 'total_horas', 'total_retardos',
            'faltas_del_periodo', 'faltas_justificadas', 'total_faltas', 'diferencia_HHMMSS'
        ]

        for columna in columnas_esperadas:
            assert columna in resultado.columns 