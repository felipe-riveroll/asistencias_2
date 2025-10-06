import pytest
import pandas as pd
from datetime import timedelta

from data_processor import AttendanceProcessor
from utils import td_to_str


@pytest.fixture
def processor():
    return AttendanceProcessor()


def test_calculo_descanso_estandar(processor):
    """Calcula 1 hora de descanso cuando existen 4 checados válidos."""
    df_dia = pd.Series(
        {
            "checado_1": "08:00:00",
            "checado_2": "13:00:00",
            "checado_3": "14:00:00",
            "checado_4": "18:00:00",
        }
    )

    horas_descanso = processor.calcular_horas_descanso(df_dia)

    assert horas_descanso == timedelta(hours=1)


def test_sin_horas_descanso(processor):
    """Devuelve cero cuando no hay suficientes registros para detectar descansos."""
    df_dia = pd.Series({"checado_1": "08:00:00", "checado_2": "18:00:00"})

    horas_descanso = processor.calcular_horas_descanso(df_dia)

    assert horas_descanso == timedelta(0)


def test_checados_insuficientes_para_descanso(processor):
    """Requiere al menos cuatro checados para considerar descansos."""
    df_dia = pd.Series(
        {
            "checado_1": "08:00:00",
            "checado_2": "12:00:00",
            "checado_3": "18:00:00",
        }
    )

    horas_descanso = processor.calcular_horas_descanso(df_dia)

    assert horas_descanso == timedelta(0)


def test_turno_con_medianoche(processor):
    """Reconoce descansos que cruzan medianoche."""
    df_dia = pd.Series(
        {
            "checado_1": "22:00:00",
            "checado_2": "23:30:00",
            "checado_3": "00:30:00",
            "checado_4": "06:00:00",
        }
    )

    horas_descanso = processor.calcular_horas_descanso(df_dia)

    assert horas_descanso == timedelta(hours=1)


def test_dia_con_dos_descansos(processor):
    """Suma múltiples intervalos de descanso en el mismo día."""
    df_dia = pd.Series(
        {
            "checado_1": "08:00:00",
            "checado_2": "12:00:00",
            "checado_3": "13:00:00",
            "checado_4": "17:00:00",
            "checado_5": "18:00:00",
            "checado_6": "22:00:00",
        }
    )

    horas_descanso = processor.calcular_horas_descanso(df_dia)

    assert horas_descanso == timedelta(hours=2)


def test_intervalos_cortos_no_se_cuentan(processor):
    """Ignora descansos menores o iguales a cinco minutos."""
    df_dia = pd.Series(
        {
            "checado_1": "08:00:00",
            "checado_2": "12:00:00",
            "checado_3": "12:04:00",
            "checado_4": "17:00:00",
        }
    )

    horas_descanso = processor.calcular_horas_descanso(df_dia)

    assert horas_descanso == timedelta(0)


def test_aplicar_calculo_horas_descanso_agrega_columnas(processor):
    """Agrega columnas de referencia sin modificar las horas originales."""
    df = pd.DataFrame(
        {
            "employee": [1, 2],
            "dia": ["2025-01-01", "2025-01-01"],
            "checado_1": ["08:00:00", "09:00:00"],
            "checado_2": ["13:00:00", "19:00:00"],
            "checado_3": ["14:00:00", None],
            "checado_4": ["18:00:00", None],
            "duration": ["10:00:00", "10:00:00"],
            "horas_trabajadas": ["10:00:00", "10:00:00"],
            "horas_esperadas": ["08:00:00", "08:00:00"],
        }
    )

    resultado = processor.aplicar_calculo_horas_descanso(df.copy())

    emp1 = resultado[resultado["employee"] == 1].iloc[0]
    emp2 = resultado[resultado["employee"] == 2].iloc[0]

    assert emp1["horas_descanso"] == "01:00:00"
    assert emp2["horas_descanso"] == "00:00:00"

    # Las columnas originales se preservan
    assert emp1["horas_trabajadas"] == "10:00:00"
    assert emp1["horas_esperadas"] == "08:00:00"
    assert "horas_trabajadas_originales" in resultado.columns
    assert "horas_esperadas_originales" in resultado.columns


def test_td_to_str_preserva_duracion_mayor_24_horas():
    """Convierte timedelta sin perder la parte de días."""
    td_25_horas = pd.Timedelta(hours=25, minutes=30, seconds=45)

    assert td_to_str(td_25_horas) == "25:30:45"
