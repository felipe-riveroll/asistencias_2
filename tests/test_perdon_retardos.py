import pytest
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Agregar el directorio raíz al path para importar el módulo principal
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generar_reporte_optimizado import aplicar_regla_perdon_retardos


class TestPerdonRetardos:
    """Tests para la funcionalidad de perdón de retardos por cumplimiento de horas."""

    def test_retardo_perdonado_por_cumplir_horas(self):
        """Test: Retardo perdonado cuando llega tarde pero cumple las horas."""
        # Crear DataFrame de prueba
        data = {
            "employee": ["EMP001"],
            "dia": [datetime(2025, 7, 1).date()],
            "tipo_retardo": ["Retardo"],
            "minutos_tarde": [20],
            "horas_trabajadas": ["08:30:00"],  # Trabajó más de las 8 horas esperadas
            "horas_esperadas": ["08:00:00"],
        }
        df = pd.DataFrame(data)

        # Aplicar regla de perdón
        df_resultado = aplicar_regla_perdon_retardos(df)

        # Verificar que el retardo fue perdonado
        assert df_resultado.iloc[0]["retardo_perdonado"] == True
        assert df_resultado.iloc[0]["tipo_retardo"] == "A Tiempo (Cumplió Horas)"
        assert df_resultado.iloc[0]["minutos_tarde"] == 0
        assert df_resultado.iloc[0]["tipo_retardo_original"] == "Retardo"
        assert df_resultado.iloc[0]["minutos_tarde_original"] == 20
        assert df_resultado.iloc[0]["es_retardo_acumulable"] == 0

    def test_retardo_no_perdonado_por_no_cumplir_horas(self):
        """Test: Retardo NO perdonado cuando no cumple las horas."""
        # Crear DataFrame de prueba
        data = {
            "employee": ["EMP002"],
            "dia": [datetime(2025, 7, 1).date()],
            "tipo_retardo": ["Retardo"],
            "minutos_tarde": [30],
            "horas_trabajadas": ["07:30:00"],  # Trabajó menos de las 8 horas esperadas
            "horas_esperadas": ["08:00:00"],
        }
        df = pd.DataFrame(data)

        # Aplicar regla de perdón
        df_resultado = aplicar_regla_perdon_retardos(df)

        # Verificar que el retardo NO fue perdonado
        assert df_resultado.iloc[0]["retardo_perdonado"] == False
        assert df_resultado.iloc[0]["tipo_retardo"] == "Retardo"
        assert df_resultado.iloc[0]["minutos_tarde"] == 30
        assert df_resultado.iloc[0]["es_retardo_acumulable"] == 1

    def test_permiso_horas_cero_perdona_retardo(self):
        """Test: Permiso que ajusta horas_esperadas a 0, cualquier trabajo perdona el retardo."""
        # Crear DataFrame de prueba
        data = {
            "employee": ["EMP003"],
            "dia": [datetime(2025, 7, 1).date()],
            "tipo_retardo": ["Retardo"],
            "minutos_tarde": [45],
            "horas_trabajadas": ["04:00:00"],  # Trabajó algo
            "horas_esperadas": ["00:00:00"],  # Ajustado por permiso
        }
        df = pd.DataFrame(data)

        # Aplicar regla de perdón
        df_resultado = aplicar_regla_perdon_retardos(df)

        # Verificar que el retardo fue perdonado (cualquier trabajo > 0 horas)
        assert df_resultado.iloc[0]["retardo_perdonado"] == True
        assert df_resultado.iloc[0]["tipo_retardo"] == "A Tiempo (Cumplió Horas)"
        assert df_resultado.iloc[0]["es_retardo_acumulable"] == 0

    def test_turno_medianoche_llega_tarde_pero_cumple_horas(self):
        """Test: Turno que cruza medianoche, llega tarde pero cumple horas totales."""
        # Crear DataFrame de prueba
        data = {
            "employee": ["EMP004"],
            "dia": [datetime(2025, 7, 1).date()],
            "tipo_retardo": ["Retardo"],
            "minutos_tarde": [60],
            "horas_trabajadas": ["08:30:00"],  # Trabajó más de las 8 horas esperadas
            "horas_esperadas": ["08:00:00"],
        }
        df = pd.DataFrame(data)

        # Aplicar regla de perdón
        df_resultado = aplicar_regla_perdon_retardos(df)

        # Verificar que el retardo fue perdonado
        assert df_resultado.iloc[0]["retardo_perdonado"] == True
        assert df_resultado.iloc[0]["tipo_retardo"] == "A Tiempo (Cumplió Horas)"
        assert df_resultado.iloc[0]["es_retardo_acumulable"] == 0

    def test_falta_injustificada_no_perdonada_por_defecto(self):
        """Test: Falta injustificada NO perdonada por defecto (flag desactivado)."""
        # Crear DataFrame de prueba
        data = {
            "employee": ["EMP005"],
            "dia": [datetime(2025, 7, 1).date()],
            "tipo_retardo": ["Falta Injustificada"],
            "minutos_tarde": [90],
            "horas_trabajadas": ["08:30:00"],  # Trabajó más de las 8 horas esperadas
            "horas_esperadas": ["08:00:00"],
        }
        df = pd.DataFrame(data)

        # Aplicar regla de perdón (con flag desactivado por defecto)
        df_resultado = aplicar_regla_perdon_retardos(df)

        # Verificar que la falta injustificada NO fue perdonada
        assert df_resultado.iloc[0]["retardo_perdonado"] == False
        assert df_resultado.iloc[0]["tipo_retardo"] == "Falta Injustificada"
        assert df_resultado.iloc[0]["es_falta"] == 1

    def test_recalculo_retardos_acumulados(self):
        """Test: Verificar que los retardos acumulados se recalculan correctamente."""
        # Crear DataFrame de prueba con múltiples días
        data = {
            "employee": ["EMP006", "EMP006", "EMP006"],
            "dia": [
                datetime(2025, 7, 1).date(),
                datetime(2025, 7, 2).date(),
                datetime(2025, 7, 3).date(),
            ],
            "tipo_retardo": ["Retardo", "Retardo", "A Tiempo"],
            "minutos_tarde": [20, 30, 0],
            "horas_trabajadas": [
                "08:30:00",
                "07:30:00",
                "08:00:00",
            ],  # Solo el primero cumple
            "horas_esperadas": ["08:00:00", "08:00:00", "08:00:00"],
        }
        df = pd.DataFrame(data)

        # Aplicar regla de perdón
        df_resultado = aplicar_regla_perdon_retardos(df)

        # Verificar que solo el segundo retardo se cuenta (el primero fue perdonado)
        assert df_resultado.iloc[0]["es_retardo_acumulable"] == 0  # Perdonado
        assert df_resultado.iloc[1]["es_retardo_acumulable"] == 1  # No perdonado
        assert df_resultado.iloc[2]["es_retardo_acumulable"] == 0  # A tiempo

        # Verificar retardos acumulados
        assert df_resultado.iloc[0]["retardos_acumulados"] == 0
        assert df_resultado.iloc[1]["retardos_acumulados"] == 1
        assert df_resultado.iloc[2]["retardos_acumulados"] == 1

    def test_descuento_por_3_retardos_recalculado(self):
        """Test: Verificar que el descuento por 3 retardos se recalcula correctamente."""
        # Crear DataFrame de prueba con 4 retardos (el primero será perdonado)
        data = {
            "employee": ["EMP007", "EMP007", "EMP007", "EMP007"],
            "dia": [
                datetime(2025, 7, 1).date(),
                datetime(2025, 7, 2).date(),
                datetime(2025, 7, 3).date(),
                datetime(2025, 7, 4).date(),
            ],
            "tipo_retardo": ["Retardo", "Retardo", "Retardo", "Retardo"],
            "minutos_tarde": [20, 30, 25, 35],
            "horas_trabajadas": [
                "08:30:00",
                "07:30:00",
                "07:30:00",
                "07:30:00",
            ],  # Solo el primero cumple
            "horas_esperadas": ["08:00:00", "08:00:00", "08:00:00", "08:00:00"],
        }
        df = pd.DataFrame(data)

        # Aplicar regla de perdón
        df_resultado = aplicar_regla_perdon_retardos(df)

        # Verificar retardos acumulados después del perdón
        assert df_resultado.iloc[0]["retardos_acumulados"] == 0  # Perdonado
        assert df_resultado.iloc[1]["retardos_acumulados"] == 1
        assert df_resultado.iloc[2]["retardos_acumulados"] == 2
        assert df_resultado.iloc[3]["retardos_acumulados"] == 3

        # Verificar descuento por 3er retardo
        assert df_resultado.iloc[0]["descuento_por_3_retardos"] == "No"
        assert df_resultado.iloc[1]["descuento_por_3_retardos"] == "No"
        assert df_resultado.iloc[2]["descuento_por_3_retardos"] == "No"
        assert df_resultado.iloc[3]["descuento_por_3_retardos"] == "Sí (3er retardo)"

    def test_manejo_valores_nulos_y_especiales(self):
        """Test: Verificar manejo correcto de valores nulos y especiales."""
        # Crear DataFrame de prueba con valores problemáticos
        data = {
            "employee": ["EMP008", "EMP009", "EMP010"],
            "dia": [
                datetime(2025, 7, 1).date(),
                datetime(2025, 7, 1).date(),
                datetime(2025, 7, 1).date(),
            ],
            "tipo_retardo": ["Retardo", "Retardo", "Retardo"],
            "minutos_tarde": [20, 30, 40],
            "horas_trabajadas": [None, "00:00:00", "---"],  # Valores problemáticos
            "horas_esperadas": ["08:00:00", "08:00:00", "08:00:00"],
        }
        df = pd.DataFrame(data)

        # Aplicar regla de perdón
        df_resultado = aplicar_regla_perdon_retardos(df)

        # Verificar que no se aplicó perdón a valores problemáticos
        assert df_resultado.iloc[0]["retardo_perdonado"] == False
        assert df_resultado.iloc[1]["retardo_perdonado"] == False
        assert df_resultado.iloc[2]["retardo_perdonado"] == False

    def test_dataframe_vacio(self):
        """Test: Verificar manejo correcto de DataFrame vacío."""
        df_vacio = pd.DataFrame()
        df_resultado = aplicar_regla_perdon_retardos(df_vacio)

        assert df_resultado.empty

    def test_preservacion_otras_columnas(self):
        """Test: Verificar que otras columnas del DataFrame se preservan."""
        # Crear DataFrame de prueba con columnas adicionales
        data = {
            "employee": ["EMP011"],
            "dia": [datetime(2025, 7, 1).date()],
            "tipo_retardo": ["Retardo"],
            "minutos_tarde": [20],
            "horas_trabajadas": ["08:30:00"],
            "horas_esperadas": ["08:00:00"],
            "columna_adicional": ["valor_test"],
        }
        df = pd.DataFrame(data)

        # Aplicar regla de perdón
        df_resultado = aplicar_regla_perdon_retardos(df)

        # Verificar que la columna adicional se preserva
        assert "columna_adicional" in df_resultado.columns
        assert df_resultado.iloc[0]["columna_adicional"] == "valor_test"
