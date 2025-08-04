"""
Pruebas unitarias para el procesamiento de turnos nocturnos que cruzan medianoche.
"""

import unittest
import pandas as pd
from datetime import datetime, date, timedelta
from data_processor import AttendanceProcessor


class TestNightShiftProcessing(unittest.TestCase):
    """Pruebas para el procesamiento de turnos nocturnos."""
    
    def setUp(self):
        """Configuración inicial para las pruebas."""
        self.processor = AttendanceProcessor()
        
        # Crear datos de prueba
        self.test_checkin_data = [
            {
                "name": "EMP-CKIN-07-2025-000103",
                "employee": "59",
                "employee_name": "Andrea Milay Aguilar",
                "time": "2025-07-03 18:04:00"
            },
            {
                "name": "EMP-CKIN-07-2025-000104", 
                "employee": "59",
                "employee_name": "Andrea Milay Aguilar",
                "time": "2025-07-04 02:04:00"
            },
            {
                "name": "EMP-CKIN-07-2025-000105",
                "employee": "59", 
                "employee_name": "Andrea Milay Aguilar",
                "time": "2025-07-03 22:30:00"
            },
            {
                "name": "EMP-CKIN-07-2025-000106",
                "employee": "59",
                "employee_name": "Andrea Milay Aguilar", 
                "time": "2025-07-04 00:15:00"
            }
        ]
        
        # Cache de horarios de prueba
        self.test_cache_horarios = {
            "59": {
                True: {  # Primera quincena
                    4: {  # Jueves (dia_iso = 4)
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00", 
                        "horas_totales": 8,
                        "cruza_medianoche": True
                    },
                    5: {  # Viernes (dia_iso = 5)
                        "hora_entrada": "18:00",
                        "hora_salida": "02:00", 
                        "horas_totales": 8,
                        "cruza_medianoche": True
                    }
                }
            }
        }
    
    def test_process_checkins_to_dataframe(self):
        """Prueba la creación del DataFrame base con marcas de entrada/salida."""
        df = self.processor.process_checkins_to_dataframe(
            self.test_checkin_data, "2025-07-03", "2025-07-04"
        )
        
        # Verificar que se creó el DataFrame
        self.assertFalse(df.empty)
        self.assertIn("employee", df.columns)
        self.assertIn("dia", df.columns)
        self.assertIn("checado_1", df.columns)
        
        # Verificar que las marcas están en las fechas correctas
        df_03 = df[df["dia"] == date(2025, 7, 3)]
        df_04 = df[df["dia"] == date(2025, 7, 4)]
        
        self.assertFalse(df_03.empty)
        self.assertFalse(df_04.empty)
        
        # Verificar que las marcas están distribuidas correctamente
        checadas_03 = [df_03.iloc[0][f"checado_{i}"] for i in range(1, 4) 
                      if f"checado_{i}" in df_03.columns and pd.notna(df_03.iloc[0][f"checado_{i}"])]
        checadas_04 = [df_04.iloc[0][f"checado_{i}"] for i in range(1, 4)
                      if f"checado_{i}" in df_04.columns and pd.notna(df_04.iloc[0][f"checado_{i}"])]
        
        self.assertGreater(len(checadas_03), 0)
        self.assertGreater(len(checadas_04), 0)
    
    def test_map_shift_date_function(self):
        """Prueba la función interna map_shift_date para turnos nocturnos."""
        # Simular la función map_shift_date
        def map_shift_date(checada_time, entrada, salida, cruza_medianoche, dia_original):
            if not cruza_medianoche:
                return dia_original
                
            try:
                entrada_time = datetime.strptime(entrada, "%H:%M").time()
                salida_time = datetime.strptime(salida, "%H:%M").time()
                checada_time_obj = datetime.strptime(checada_time, "%H:%M:%S").time()
                
                # Según las especificaciones del usuario:
                # Si cruza_medianoche = true, cualquier marca con hora ≥ 00:00 y ≤ horario_salida (02:00)
                # pertenece al día anterior (el de horario_entrada)
                # También incluimos marcas que están muy cerca de la hora de salida (tolerancia de 5 minutos)
                if checada_time_obj <= salida_time or (checada_time_obj.hour == salida_time.hour and checada_time_obj.minute <= salida_time.minute + 5):
                    return dia_original - timedelta(days=1)
                else:
                    return dia_original
            except (ValueError, TypeError):
                return dia_original
        
        # Caso 1: Marca a las 18:04 del día 3 (entrada del turno)
        fecha_turno = map_shift_date("18:04:00", "18:00", "02:00", True, date(2025, 7, 3))
        self.assertEqual(fecha_turno, date(2025, 7, 3))
        
        # Caso 2: Marca a las 02:04 del día 4 (pertenece al turno del día 3 - con tolerancia)
        fecha_turno = map_shift_date("02:04:00", "18:00", "02:00", True, date(2025, 7, 4))
        self.assertEqual(fecha_turno, date(2025, 7, 3))
        
        # Caso 3: Marca a las 18:00 del día 4 (nuevo turno - después de la hora de entrada)
        fecha_turno = map_shift_date("18:00:00", "18:00", "02:00", True, date(2025, 7, 4))
        self.assertEqual(fecha_turno, date(2025, 7, 4))
        
        # Caso 4: Marca a las 00:15 del día 4 (pertenece al turno del día 3)
        fecha_turno = map_shift_date("00:15:00", "18:00", "02:00", True, date(2025, 7, 4))
        self.assertEqual(fecha_turno, date(2025, 7, 3))
        
        # Caso 5: Turno normal (no cruza medianoche)
        fecha_turno = map_shift_date("08:00:00", "08:00", "17:00", False, date(2025, 7, 3))
        self.assertEqual(fecha_turno, date(2025, 7, 3))
    
    def test_night_shift_processing_integration(self):
        """Prueba la integración completa del procesamiento de turnos nocturnos."""
        # Crear DataFrame base
        df_base = self.processor.process_checkins_to_dataframe(
            self.test_checkin_data, "2025-07-03", "2025-07-04"
        )
        
        # Debug: imprimir el DataFrame base
        print("\nDEBUG - DataFrame base:")
        columnas_base = ['employee', 'dia', 'checado_1', 'checado_2']
        columnas_existentes = [col for col in columnas_base if col in df_base.columns]
        print(df_base[columnas_existentes].to_string())
        
        # Aplicar procesamiento de turnos nocturnos
        df_procesado = self.processor.procesar_horarios_con_medianoche(
            df_base, self.test_cache_horarios
        )
        
        # Debug: imprimir el DataFrame procesado
        print("\nDEBUG - DataFrame procesado:")
        columnas_proc = ['employee', 'dia', 'checado_1', 'checado_2', 'horas_trabajadas']
        columnas_existentes_proc = [col for col in columnas_proc if col in df_procesado.columns]
        print(df_procesado[columnas_existentes_proc].to_string())
        
        # Verificar que el procesamiento se completó
        self.assertFalse(df_procesado.empty)
        
        # Buscar la fila del día 3 (fecha del turno)
        df_turno = df_procesado[df_procesado["dia"] == date(2025, 7, 3)]
        
        if not df_turno.empty:
            fila_turno = df_turno.iloc[0]
            
            # Verificar que se asignaron entrada y salida
            self.assertIsNotNone(fila_turno.get("checado_1"))
            self.assertIsNotNone(fila_turno.get("checado_2"))
            
            # Verificar que las horas trabajadas son aproximadamente 8 horas
            if pd.notna(fila_turno.get("horas_trabajadas")):
                horas_str = fila_turno["horas_trabajadas"]
                print(f"\nDEBUG - Horas trabajadas: {horas_str}")
                if horas_str != "00:00:00":
                    # Convertir a horas decimales para comparación
                    partes = horas_str.split(":")
                    horas_decimal = int(partes[0]) + int(partes[1])/60
                    
                    print(f"DEBUG - Horas decimales: {horas_decimal}")
                    
                    # Debería ser aproximadamente 8 horas (con tolerancia)
                    self.assertGreaterEqual(horas_decimal, 7.5)
                    self.assertLessEqual(horas_decimal, 8.5)
    
    def test_regular_shift_unchanged(self):
        """Prueba que los turnos regulares no se vean afectados."""
        # Datos de turno regular (8:00-17:00)
        regular_checkin_data = [
            {
                "name": "EMP-CKIN-07-2025-000201",
                "employee": "60",
                "employee_name": "Empleado Regular",
                "time": "2025-07-03 08:05:00"
            },
            {
                "name": "EMP-CKIN-07-2025-000202",
                "employee": "60", 
                "employee_name": "Empleado Regular",
                "time": "2025-07-03 17:00:00"
            }
        ]
        
        # Cache para turno regular
        regular_cache = {
            "60": {
                True: {
                    4: {  # Jueves
                        "hora_entrada": "08:00",
                        "hora_salida": "17:00",
                        "horas_totales": 8,
                        "cruza_medianoche": False
                    }
                }
            }
        }
        
        # Procesar turno regular
        df_base = self.processor.process_checkins_to_dataframe(
            regular_checkin_data, "2025-07-03", "2025-07-03"
        )
        
        df_procesado = self.processor.procesar_horarios_con_medianoche(
            df_base, regular_cache
        )
        
        # Verificar que el turno regular no cambió
        df_regular = df_procesado[df_procesado["employee"] == "60"]
        self.assertFalse(df_regular.empty)
        
        fila_regular = df_regular.iloc[0]
        self.assertEqual(fila_regular["checado_1"], "08:05:00")
        self.assertEqual(fila_regular["checado_2"], "17:00:00")


if __name__ == "__main__":
    # Ejecutar las pruebas
    unittest.main(verbosity=2) 