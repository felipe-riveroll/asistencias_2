#!/usr/bin/env python
"""
Script de prueba para verificar los cambios implementados:
1. Función format_timedelta_without_plus_sign()
2. Colores en el Excel
"""

import pandas as pd
from datetime import timedelta
from utils import format_timedelta_without_plus_sign, format_timedelta_with_sign
from report_generator import ReportGenerator
from reporte_excel import generar_reporte_excel


def test_format_functions():
    """Probar las funciones de formateo."""
    print("Probando funciones de formateo...")

    test_cases = [
        timedelta(hours=2, minutes=30),  # Positivo
        timedelta(hours=-1, minutes=-15),  # Negativo
        timedelta(0),  # Cero
    ]

    for td in test_cases:
        old_format = format_timedelta_with_sign(td)
        new_format = format_timedelta_without_plus_sign(td)
        print(f"  Original: {old_format} -> Nuevo: {new_format}")


def test_excel_report():
    """Probar la generación del reporte Excel con los nuevos cambios."""
    print("\nGenerando reporte Excel de prueba...")

    # Crear datos de prueba
    df_detalle = pd.DataFrame(
        {
            "employee": ["EMP001", "EMP002", "EMP003"],
            "Nombre": ["Juan Pérez", "María García", "Carlos López"],
            "dia": ["2025-01-15", "2025-01-15", "2025-01-15"],
            "horas_trabajadas": ["09:00:00", "07:30:00", "08:00:00"],
            "horas_esperadas": ["08:00:00", "08:00:00", "08:00:00"],
        }
    )

    # Crear resumen con diferentes tipos de diferencias
    df_resumen = pd.DataFrame(
        {
            "employee": ["EMP001", "EMP002", "EMP003"],
            "Nombre": ["Juan Pérez", "María García", "Carlos López"],
            "total_horas_trabajadas": ["09:00:00", "07:30:00", "08:00:00"],
            "total_horas_esperadas": ["08:00:00", "08:00:00", "08:00:00"],
            "total_horas_descontadas_permiso": ["00:00:00", "00:00:00", "00:00:00"],
            "total_horas_descanso": ["00:00:00", "00:00:00", "00:00:00"],
            "total_horas": ["08:00:00", "08:00:00", "08:00:00"],
            "total_retardos": [0, 1, 0],
            "faltas_del_periodo": [0, 0, 0],
            "faltas_justificadas": [0, 0, 0],
            "total_faltas": [0, 0, 0],
            "total_salidas_anticipadas": [0, 0, 0],
            "diferencia_HHMMSS": [
                "01:00:00",
                "-00:30:00",
                "00:00:00",
            ],  # Positivo, negativo, cero
        }
    )

    # Generar el reporte Excel
    try:
        archivo_excel = generar_reporte_excel(
            df_detalle, df_resumen, "PRUEBA", "2025-01-15", "2025-01-15"
        )
        print(f"Reporte Excel generado: {archivo_excel}")
        print("   - Valores positivos en diferencia_HHMMSS deberian tener color #1cb1ee")
        print("   - Valores positivos NO deberian tener signo '+'")
        return archivo_excel
    except Exception as e:
        print(f"Error generando Excel: {e}")
        return None


if __name__ == "__main__":
    print("Probando los cambios implementados...\n")

    # Probar funciones de formateo
    test_format_functions()

    # Probar generación de Excel
    archivo = test_excel_report()

    print("\nPruebas completadas!")
    if archivo:
        print(f"   - Abrir {archivo} para verificar el formato y colores")
    print(
        "   - Los valores positivos NO deben tener '+' y deben tener fondo azul #1cb1ee"
    )
