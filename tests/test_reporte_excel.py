#!/usr/bin/env python3
"""
Script de prueba para el generador de reportes Excel con formato FRAPPE
"""

import pandas as pd
from datetime import datetime, timedelta
from reporte_excel import generar_reporte_excel

def crear_datos_prueba():
    """Crear datos de prueba simulando el formato del CSV existente"""
    
    # Datos base para el reporte detallado
    empleados = [
        {"employee": 46, "Nombre": "Mónica Graciela Jiménez López"},
        {"employee": 49, "Nombre": "Guadalupe López Rojas"},
        {"employee": 50, "Nombre": "Christian Joel Popoca Domínguez"}
    ]
    
    datos_reporte = []
    
    # Generar datos para una semana de prueba
    fecha_inicio = datetime(2025, 5, 1)
    
    for empleado in empleados:
        for i in range(7):  # Una semana
            fecha = fecha_inicio + timedelta(days=i)
            dia_semana = fecha.strftime("%A")
            
            # Traducir días al español
            dias_es = {
                "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
                "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
            }
            dia_semana_es = dias_es[dia_semana]
            
            # Simular diferentes escenarios
            if dia_semana in ["Saturday", "Sunday"]:
                # Fin de semana - algunos trabajan
                if empleado["employee"] == 46:  # Solo Mónica trabaja fin de semana
                    datos_reporte.append({
                        "employee": empleado["employee"],
                        "Nombre": empleado["Nombre"],
                        "dia": fecha.strftime("%Y-%m-%d"),
                        "dia_semana": dia_semana_es,
                        "hora_entrada_programada": "09:00",
                        "checado_1": "09:01:09",
                        "checado_2": "17:10:05",
                        "checado_3": "",
                        "checado_4": "",
                        "checado_5": "",
                        "horas_esperadas": "8:00:00",
                        "horas_trabajadas": "08:08:56",
                        "horas_descanso": "00:00:00",
                        "tipo_retardo": "A Tiempo",
                        "tiene_permiso": False,
                        "tipo_permiso": "",
                        "salida_anticipada": False
                    })
                else:
                    datos_reporte.append({
                        "employee": empleado["employee"],
                        "Nombre": empleado["Nombre"],
                        "dia": fecha.strftime("%Y-%m-%d"),
                        "dia_semana": dia_semana_es,
                        "hora_entrada_programada": "---",
                        "checado_1": "---",
                        "checado_2": "---",
                        "checado_3": "---",
                        "checado_4": "---",
                        "checado_5": "---",
                        "horas_esperadas": "---",
                        "horas_trabajadas": "---",
                        "horas_descanso": "---",
                        "tipo_retardo": "Día no Laborable",
                        "tiene_permiso": False,
                        "tipo_permiso": "",
                        "salida_anticipada": False
                    })
            else:
                # Días laborables
                escenarios = [
                    # A tiempo (sin color)
                    {
                        "checado_1": "08:00:00", "tipo_retardo": "A Tiempo",
                        "checado_2": "17:00:00", "horas_trabajadas": "09:00:00",
                        "horas_descanso": "01:00:00", "retardo_perdonado": False,
                        "tiene_permiso": False
                    },
                    # Retardo menor NO perdonado (amarillo #FFFF00)
                    {
                        "checado_1": "08:15:00", "tipo_retardo": "Retardo",
                        "checado_2": "17:00:00", "horas_trabajadas": "08:45:00",
                        "horas_descanso": "00:00:00", "retardo_perdonado": False,
                        "tiene_permiso": False
                    },
                    # Retardo mayor NO perdonado (rojo #FF0000)
                    {
                        "checado_1": "08:45:00", "tipo_retardo": "Retardo",
                        "checado_2": "16:30:00", "horas_trabajadas": "07:45:00",
                        "horas_descanso": "00:00:00", "retardo_perdonado": False,
                        "tiene_permiso": False
                    },
                    # Retardo perdonado (SIN COLOR - normal)
                    {
                        "checado_1": "08:30:00", "tipo_retardo": "A Tiempo (Cumplió Horas)",
                        "checado_2": "17:30:00", "horas_trabajadas": "09:00:00",
                        "horas_descanso": "00:00:00", "retardo_perdonado": True,
                        "tiene_permiso": False
                    },
                    # Día con permiso (fecha verde claro, checada sin color)
                    {
                        "checado_1": "08:00:00", "tipo_retardo": "A Tiempo",
                        "checado_2": "13:00:00", "horas_trabajadas": "05:00:00",
                        "horas_descanso": "00:00:00", "retardo_perdonado": False,
                        "tiene_permiso": True, "tipo_permiso": "Permiso médico"
                    },
                    # Turno nocturno sin entrada (entrada verde #70AD47)
                    {
                        "checado_1": "---", "tipo_retardo": "Falta Entrada Nocturno",
                        "checado_2": "02:00:00", "horas_trabajadas": "00:00:00",
                        "horas_descanso": "00:00:00", "retardo_perdonado": False,
                        "tiene_permiso": False
                    },
                    # Día no laborable (sin checadas)
                    {
                        "checado_1": "---", "tipo_retardo": "Día no Laborable",
                        "checado_2": "---", "horas_trabajadas": "---",
                        "horas_descanso": "---", "retardo_perdonado": False,
                        "tiene_permiso": False
                    }
                ]
                
                escenario = escenarios[i % len(escenarios)]
                
                datos_reporte.append({
                    "employee": empleado["employee"],
                    "Nombre": empleado["Nombre"],
                    "dia": fecha.strftime("%Y-%m-%d"),
                    "dia_semana": dia_semana_es,
                    "hora_entrada_programada": "08:00",
                    "checado_1": escenario["checado_1"],
                    "checado_2": escenario["checado_2"],
                    "checado_3": "",
                    "checado_4": "",
                    "checado_5": "",
                    "horas_esperadas": "8:00:00",
                    "horas_trabajadas": escenario["horas_trabajadas"],
                    "horas_descanso": escenario["horas_descanso"],
                    "tipo_retardo": escenario["tipo_retardo"],
                    "retardo_perdonado": escenario["retardo_perdonado"],
                    "tiene_permiso": escenario["tiene_permiso"],
                    "tipo_permiso": escenario.get("tipo_permiso", ""),
                    "salida_anticipada": False
                })
    
    df_reporte = pd.DataFrame(datos_reporte)
    
    # Datos de resumen
    datos_resumen = []
    for empleado in empleados:
        datos_resumen.append({
            "employee": empleado["employee"],
            "Nombre": empleado["Nombre"],
            "total_horas_trabajadas": "40:00:00",
            "total_horas_esperadas": "40:00:00",
            "total_retardos": 2,
            "faltas_del_periodo": 0,
            "total_faltas": 0
        })
    
    df_resumen = pd.DataFrame(datos_resumen)
    
    return df_reporte, df_resumen

def main():
    """Función principal de prueba"""
    print("🚀 Iniciando prueba de generación de reporte Excel FRAPPE...")
    
    # Crear datos de prueba
    df_reporte, df_resumen = crear_datos_prueba()
    
    print(f"📊 Datos de prueba creados:")
    print(f"   - {len(df_reporte)} registros de detalle")
    print(f"   - {len(df_resumen)} empleados en resumen")
    
    # Generar reporte Excel
    try:
        archivo_excel = generar_reporte_excel(
            df_reporte=df_reporte,
            df_resumen=df_resumen,
            sucursal="Villas_Test",
            periodo_inicio="2025-05-01",
            periodo_fin="2025-05-07"
        )
        
        print(f"✅ Reporte Excel generado exitosamente: {archivo_excel}")
        print(f"📄 El archivo incluye:")
        print(f"   - Hoja 'Detalle Asistencia' con formato FRAPPE")
        print(f"   - Colores ICG aplicados según especificaciones")
        print(f"   - Filas de totales por empleado")
        print(f"   - Formato profesional con bordes y alineación")
        
    except Exception as e:
        print(f"❌ Error al generar reporte: {e}")
        raise

if __name__ == "__main__":
    main()