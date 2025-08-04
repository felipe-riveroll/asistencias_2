"""
Test comprehensivo para validar la solución del Bug #4
"""

import pandas as pd
from datetime import date, datetime
from data_processor import AttendanceProcessor


def test_bug_4_comprehensive():
    """
    Test comprehensivo del Bug #4: múltiples casos de salidas nocturnas
    que caen en días sin horario programado
    """
    
    # Casos de prueba:
    # 1. Sábado → Domingo (caso original de Andrea)
    # 2. Viernes → Sábado (otro caso posible)
    # 3. Días con horario normal para verificar que no se afecten
    
    checkin_data = [
        # Caso 1: Andrea - Sábado nocturno → Domingo
        {"employee": "EMP001", "employee_name": "Andrea", "time": "2025-07-05 18:08:41"},
        {"employee": "EMP001", "employee_name": "Andrea", "time": "2025-07-06 02:10:56"},
        
        # Caso 2: Juan - Viernes nocturno → Sábado  
        {"employee": "EMP002", "employee_name": "Juan", "time": "2025-07-04 23:15:30"},
        {"employee": "EMP002", "employee_name": "Juan", "time": "2025-07-05 01:45:15"},
        
        # Caso 3: María - Lunes normal (no nocturno)
        {"employee": "EMP003", "employee_name": "María", "time": "2025-07-07 08:30:00"},
        {"employee": "EMP003", "employee_name": "María", "time": "2025-07-07 17:15:00"},
    ]
    
    # Cache de horarios
    cache_horarios = {
        "EMP001": {  # Andrea - solo sábados nocturnos
            True: {
                6: {  # Sábado
                    "hora_entrada": "18:00", 
                    "hora_salida": "02:00",
                    "cruza_medianoche": True,
                    "horas_totales": 8.0,
                }
            }
        },
        "EMP002": {  # Juan - viernes nocturno
            True: {
                5: {  # Viernes
                    "hora_entrada": "23:00",
                    "hora_salida": "07:00", 
                    "cruza_medianoche": True,
                    "horas_totales": 8.0,
                }
            }
        },
        "EMP003": {  # María - lunes normal
            True: {
                1: {  # Lunes
                    "hora_entrada": "08:00",
                    "hora_salida": "17:00",
                    "cruza_medianoche": False,
                    "horas_totales": 9.0,
                }
            }
        }
    }
    
    print("🧪 Test comprehensivo Bug #4...")
    print("Casos de prueba:")
    for record in checkin_data:
        print(f"  {record['employee_name']}: {record['time']}")
    print()
    
    # Procesar
    processor = AttendanceProcessor()
    df = processor.process_checkins_to_dataframe(checkin_data, "2025-07-04", "2025-07-07")
    df_processed = processor.procesar_horarios_con_medianoche(df, cache_horarios)
    
    print("Resultados por empleado:")
    
    for empleado in ["EMP001", "EMP002", "EMP003"]:
        nombre = {"EMP001": "Andrea", "EMP002": "Juan", "EMP003": "María"}[empleado]
        print(f"\n{nombre} ({empleado}):")
        
        emp_data = df_processed[df_processed['employee'] == empleado]
        
        for _, row in emp_data.iterrows():
            if pd.notna(row.get('checado_1')) or pd.notna(row.get('checado_2')):
                entrada = row.get('checado_1', 'None')
                salida = row.get('checado_2', 'None')
                print(f"  {row['dia']}: entrada={entrada}, salida={salida}")
    
    # Validaciones específicas del Bug #4
    print("\n✅ Validaciones:")
    
    # Caso 1: Andrea - sábado debe tener ambas marcas, domingo debe estar limpio
    andrea_sabado = df_processed[
        (df_processed['employee'] == 'EMP001') & 
        (df_processed['dia'] == date(2025, 7, 5))
    ]
    andrea_domingo = df_processed[
        (df_processed['employee'] == 'EMP001') & 
        (df_processed['dia'] == date(2025, 7, 6))
    ]
    
    assert not andrea_sabado.empty, "Andrea debe tener registro el sábado"
    sabado = andrea_sabado.iloc[0]
    assert sabado['checado_1'] == '18:08:41', f"Entrada sábado incorrecta: {sabado['checado_1']}"
    assert sabado['checado_2'] == '02:10:56', f"Salida sábado incorrecta: {sabado['checado_2']}"
    print("✓ Andrea: Sábado tiene entrada y salida correctas")
    
    if not andrea_domingo.empty:
        domingo = andrea_domingo.iloc[0]
        assert pd.isna(domingo.get('checado_1')) or domingo.get('checado_1') is None, \
            f"Domingo debe estar limpio, pero tiene: {domingo.get('checado_1')}"
        print("✓ Andrea: Domingo limpio (sin marcas fantasma)")
    
    # Caso 2: Juan - viernes debe tener ambas marcas, sábado debe estar limpio  
    juan_viernes = df_processed[
        (df_processed['employee'] == 'EMP002') & 
        (df_processed['dia'] == date(2025, 7, 4))
    ]
    juan_sabado = df_processed[
        (df_processed['employee'] == 'EMP002') & 
        (df_processed['dia'] == date(2025, 7, 5))
    ]
    
    assert not juan_viernes.empty, "Juan debe tener registro el viernes"
    viernes = juan_viernes.iloc[0]
    assert viernes['checado_1'] == '23:15:30', f"Entrada viernes incorrecta: {viernes['checado_1']}"
    assert viernes['checado_2'] == '01:45:15', f"Salida viernes incorrecta: {viernes['checado_2']}"
    print("✓ Juan: Viernes tiene entrada y salida correctas")
    
    if not juan_sabado.empty:
        sabado_j = juan_sabado.iloc[0]
        assert pd.isna(sabado_j.get('checado_1')) or sabado_j.get('checado_1') is None, \
            f"Sábado de Juan debe estar limpio, pero tiene: {sabado_j.get('checado_1')}"
        print("✓ Juan: Sábado limpio (sin marcas fantasma)")
    
    # Caso 3: María - turno normal no debe verse afectado
    maria_lunes = df_processed[
        (df_processed['employee'] == 'EMP003') & 
        (df_processed['dia'] == date(2025, 7, 7))
    ]
    
    assert not maria_lunes.empty, "María debe tener registro el lunes"
    lunes = maria_lunes.iloc[0]
    assert lunes['checado_1'] == '08:30:00', f"Entrada lunes incorrecta: {lunes['checado_1']}"
    assert lunes['checado_2'] == '17:15:00', f"Salida lunes incorrecta: {lunes['checado_2']}"
    print("✓ María: Turno normal no afectado")
    
    print("\n🎉 Bug #4 completamente arreglado - Todos los casos pasan!")


if __name__ == "__main__":
    test_bug_4_comprehensive()