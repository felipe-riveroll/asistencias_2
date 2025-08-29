"""
Test para reproducir Bug #4: Salidas nocturnas se pierden cuando caen en días sin horario
"""

import pandas as pd
from datetime import date, datetime
from data_processor import AttendanceProcessor


def test_bug_4_last_day_checkout():
    """
    Caso reproducible: Andrea, sáb 05-jul-2025
    - Checada 1: 2025-07-05 18:08:41
    - Checada 2: 2025-07-06 02:10:56

    Esperado: Ambas marcas deben asignarse al sábado 5 de julio
    """

    # Simular datos de check-ins como vienen de la API
    checkin_data = [
        {
            "employee": "EMP001",
            "employee_name": "Andrea",
            "time": "2025-07-05 18:08:41",
        },
        {
            "employee": "EMP001",
            "employee_name": "Andrea",
            "time": "2025-07-06 02:10:56",
        },
    ]

    # Cache de horarios - sábado tiene turno nocturno, domingo no
    cache_horarios = {
        "EMP001": {
            True: {  # Primera quincena
                6: {  # Sábado
                    "hora_entrada": "18:00",
                    "hora_salida": "02:00",
                    "cruza_medianoche": True,
                    "horas_totales": 8.0,
                },
                # Domingo (7) no tiene horario programado
            }
        }
    }

    print("🧪 Reproducing Bug #4...")
    print("Datos de entrada:")
    for record in checkin_data:
        print(f"  {record['employee']}: {record['time']}")
    print()

    # Procesar como lo hace el sistema real
    processor = AttendanceProcessor()

    # Paso 1: Crear DataFrame base
    df = processor.process_checkins_to_dataframe(
        checkin_data, "2025-07-05", "2025-07-07"
    )

    print("DataFrame después de process_checkins_to_dataframe:")
    print("Columnas disponibles:", df.columns.tolist())
    print(
        df[
            ["employee", "dia"]
            + [col for col in df.columns if col.startswith("checado_")]
        ]
    )
    print()

    # Paso 2: Procesar cruce de medianoche
    df_processed = processor.procesar_horarios_con_medianoche(df, cache_horarios)

    print("DataFrame después de procesar_horarios_con_medianoche:")
    print("Columnas disponibles:", df_processed.columns.tolist())
    checado_cols = [col for col in df_processed.columns if col.startswith("checado_")]
    if checado_cols:
        print(df_processed[["employee", "dia"] + checado_cols])
    else:
        print("No hay columnas checado_")
    print()

    # Verificar resultados esperados
    sabado_row = df_processed[df_processed["dia"] == date(2025, 7, 5)]
    domingo_row = df_processed[df_processed["dia"] == date(2025, 7, 6)]

    print("Verificando resultados:")
    print(f"Sábado 5: {len(sabado_row)} filas")
    if not sabado_row.empty:
        row = sabado_row.iloc[0]
        print(f"  Entrada: {row.get('checado_1', 'None')}")
        print(f"  Salida: {row.get('checado_2', 'None')}")

    print(f"Domingo 6: {len(domingo_row)} filas")
    if not domingo_row.empty:
        row = domingo_row.iloc[0]
        print(f"  Entrada: {row.get('checado_1', 'None')}")
        print(f"  Salida: {row.get('checado_2', 'None')}")

    # Assertions para el comportamiento esperado
    assert not sabado_row.empty, "Debe existir fila para el sábado"
    sabado = sabado_row.iloc[0]

    # El sábado debe tener tanto la entrada como la salida
    assert sabado["checado_1"] == "18:08:41", (
        f"Entrada esperada 18:08:41, obtenida {sabado['checado_1']}"
    )
    assert sabado["checado_2"] == "02:10:56", (
        f"Salida esperada 02:10:56, obtenida {sabado['checado_2']}"
    )

    # El domingo debe estar vacío o no tener marcas
    if not domingo_row.empty:
        domingo = domingo_row.iloc[0]
        assert pd.isna(domingo.get("checado_1")) or domingo.get("checado_1") is None, (
            "Domingo no debe tener marcas"
        )
        assert pd.isna(domingo.get("checado_2")) or domingo.get("checado_2") is None, (
            "Domingo no debe tener marcas"
        )

    print("✅ Test pasado - Bug #4 arreglado!")


if __name__ == "__main__":
    test_bug_4_last_day_checkout()
