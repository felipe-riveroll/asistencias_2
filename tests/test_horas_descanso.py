import pytest
import pandas as pd
from datetime import timedelta


@pytest.fixture
def datos_asistencia():
    data = {
        "employee": [1, 1, 1, 1, 2, 2, 3, 3, 3],
        "checado": [
            "08:00:00", "13:00:00", "14:00:00", "18:00:00",  # empleado 1: descanso 1 h
            "09:00:00", "19:00:00", None, None,            # empleado 2: sin descanso
            "08:00:00", "12:00:00", "18:00:00", None        # empleado 3: 3 checados
        ]
    }
    df = pd.DataFrame(data)
    df["checado"] = pd.to_datetime(
        df["checado"], format="%H:%M:%S", errors="coerce"
    ).dt.time
    return df


def test_calculo_descanso_estandar():
    """Prueba el cálculo estándar de horas de descanso con 4 checados válidos"""
    from generar_reporte_optimizado import calcular_horas_descanso
    import pandas as pd

    # Crear datos de prueba con 4 checados
    data = {
        "checado_1": "08:00:00",
        "checado_2": "13:00:00",
        "checado_3": "14:00:00",
        "checado_4": "18:00:00"
    }
    df_dia = pd.Series(data)

    # Calcular descanso
    horas_descanso = calcular_horas_descanso(df_dia)

    # Verificar que el descanso es 1 hora (14:00 - 13:00)
    assert horas_descanso == timedelta(hours=1)


def test_sin_horas_descanso():
    """Prueba el caso donde no hay suficientes checados para calcular descanso"""
    from generar_reporte_optimizado import calcular_horas_descanso
    import pandas as pd

    # Crear datos de prueba con solo 2 checados
    data = {
        "checado_1": "08:00:00",
        "checado_2": "18:00:00"
    }
    df_dia = pd.Series(data)

    # Calcular descanso
    horas_descanso = calcular_horas_descanso(df_dia)

    # Verificar que no hay descanso
    assert horas_descanso == timedelta(0)


def test_checados_insuficientes_para_descanso():
    """Prueba el caso donde hay menos de 4 checados registrados"""
    from generar_reporte_optimizado import calcular_horas_descanso
    import pandas as pd

    # Crear datos de prueba con 3 checados
    data = {
        "checado_1": "08:00:00",
        "checado_2": "12:00:00",
        "checado_3": "18:00:00"
    }
    df_dia = pd.Series(data)

    # Calcular descanso
    horas_descanso = calcular_horas_descanso(df_dia)

    # Verificar que no hay descanso (se necesitan al menos 4 checados)
    assert horas_descanso == timedelta(0)


def test_ajuste_horas_trabajadas_y_esperadas():
    """Prueba que las horas trabajadas y esperadas se ajusten correctamente con el descanso"""
    from generar_reporte_optimizado import aplicar_calculo_horas_descanso
    import pandas as pd

    # Crear datos de prueba
    data = {
        "employee": [1, 2],
        "dia": ["2025-01-01", "2025-01-01"],
        "checado_1": ["08:00:00", "09:00:00"],
        "checado_2": ["13:00:00", "19:00:00"],
        "checado_3": ["14:00:00", None],
        "checado_4": ["18:00:00", None],
        "horas_trabajadas": ["10:00:00", "10:00:00"],
        "horas_esperadas": ["08:00:00", "08:00:00"]
    }
    df = pd.DataFrame(data)

    # Aplicar cálculo de descanso
    df_resultado = aplicar_calculo_horas_descanso(df)

    # Verificar que el empleado 1 tiene descanso de 1 hora
    emp1 = df_resultado[df_resultado["employee"] == 1].iloc[0]
    assert emp1["horas_descanso"] == "01:00:00"

    # Verificar que las horas trabajadas se ajustaron (10:00 - 1:00 = 9:00)
    assert emp1["horas_trabajadas"] == "09:00:00"

    # Verificar que las horas esperadas se ajustaron (8:00 - 1:00 = 7:00)
    assert emp1["horas_esperadas"] == "07:00:00"

    # Verificar que el empleado 2 no tiene descanso
    emp2 = df_resultado[df_resultado["employee"] == 2].iloc[0]
    assert emp2["horas_descanso"] == "00:00:00"
    assert emp2["horas_trabajadas"] == "10:00:00"  # Sin cambios
    assert emp2["horas_esperadas"] == "08:00:00"   # Sin cambios 