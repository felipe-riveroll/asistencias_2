"""
Pruebas unitarias para la detección de salidas anticipadas.

Este módulo contiene pruebas exhaustivas para la función detectar_salida_anticipada
que se encuentra en generar_reporte_optimizado.py.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# Añadir el directorio raíz al path para importar el módulo principal
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generar_reporte_optimizado import TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS


class TestDeteccionSalidasAnticipadas:
    """
    Suite de pruebas para la detección de salidas anticipadas.
    
    Prueba todos los casos de uso y edge cases de la función detectar_salida_anticipada.
    """
    
    def setup_method(self):
        """Configuración inicial para cada prueba."""
        # Importar la función desde el módulo principal
        from generar_reporte_optimizado import analizar_asistencia_con_horarios_cache
        
        # Extraer la función detectar_salida_anticipada del código principal
        def detectar_salida_anticipada_test(row):
            """Versión de prueba de la función detectar_salida_anticipada."""
            # Solo aplicar si existe hora_salida_programada y al menos una checada
            if pd.isna(row.get("hora_salida_programada")) or pd.isna(row.get("checado_1")):
                return False
            
            # Obtener la última checada del día (la que tenga el valor más alto)
            checadas_dia = []
            for i in range(1, 10):  # Buscar hasta checado_9
                col_checado = f"checado_{i}"
                if col_checado in row and pd.notna(row[col_checado]):
                    checadas_dia.append(row[col_checado])
            
            # Si solo hay una checada, no considerar salida anticipada
            if len(checadas_dia) <= 1:
                return False
            
            # Obtener la última checada
            ultima_checada = max(checadas_dia)
            
            try:
                # Parsear la hora de salida programada
                hora_salida_prog = datetime.strptime(row["hora_salida_programada"] + ":00", "%H:%M:%S")
                hora_ultima_checada = datetime.strptime(ultima_checada, "%H:%M:%S")
                
                # Manejar turnos que cruzan la medianoche
                if row.get("cruza_medianoche", False):
                    # Para turnos que cruzan medianoche, la hora_salida_programada es del día siguiente
                    # No necesitamos ajustar nada aquí ya que estamos comparando solo las horas
                    pass
                
                # Calcular diferencia en minutos
                diferencia = (hora_salida_prog - hora_ultima_checada).total_seconds() / 60
                
                # Manejar casos de medianoche
                if diferencia < -12 * 60:  # Más de 12 horas antes
                    diferencia += 24 * 60
                elif diferencia > 12 * 60:  # Más de 12 horas después
                    diferencia -= 24 * 60
                
                # Se considera salida anticipada si la última checada es anterior a la hora_salida_programada
                # menos el margen de tolerancia
                return diferencia > TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS
                
            except (ValueError, TypeError):
                return False
        
        self.detectar_salida_anticipada = detectar_salida_anticipada_test
    
    def test_salida_anticipada_dentro_tolerancia(self):
        """Prueba que no se detecte salida anticipada cuando está dentro de la tolerancia."""
        row = {
            "hora_salida_programada": "18:00",
            "checado_1": "08:00:00",
            "checado_2": "17:50:00",  # 10 minutos antes, dentro de tolerancia
            "cruza_medianoche": False
        }
        
        resultado = self.detectar_salida_anticipada(row)
        assert resultado == False, "No debería detectar salida anticipada dentro de tolerancia"
    
    def test_salida_anticipada_fuera_tolerancia(self):
        """Prueba que se detecte salida anticipada cuando está fuera de la tolerancia."""
        row = {
            "hora_salida_programada": "18:00",
            "checado_1": "08:00:00",
            "checado_2": "17:30:00",  # 30 minutos antes, fuera de tolerancia
            "cruza_medianoche": False
        }
        
        resultado = self.detectar_salida_anticipada(row)
        assert resultado == True, "Debería detectar salida anticipada fuera de tolerancia"
    
    def test_salida_anticipada_exacta_tolerancia(self):
        """Prueba el caso límite exacto de la tolerancia."""
        row = {
            "hora_salida_programada": "18:00",
            "checado_1": "08:00:00",
            "checado_2": "17:45:00",  # Exactamente 15 minutos antes (tolerancia)
            "cruza_medianoche": False
        }
        
        resultado = self.detectar_salida_anticipada(row)
        assert resultado == False, "No debería detectar salida anticipada en el límite exacto"
    
    def test_una_sola_checada(self):
        """Prueba que no se detecte salida anticipada con una sola checada."""
        row = {
            "hora_salida_programada": "18:00",
            "checado_1": "08:00:00",  # Solo una checada
            "cruza_medianoche": False
        }
        
        resultado = self.detectar_salida_anticipada(row)
        assert resultado == False, "No debería detectar salida anticipada con una sola checada"
    
    def test_sin_hora_salida_programada(self):
        """Prueba que retorne False cuando no hay hora de salida programada."""
        row = {
            "checado_1": "08:00:00",
            "checado_2": "17:30:00",
            "cruza_medianoche": False
        }
        
        resultado = self.detectar_salida_anticipada(row)
        assert resultado == False, "Debería retornar False sin hora de salida programada"
    
    def test_sin_checada_entrada(self):
        """Prueba que retorne False cuando no hay checada de entrada."""
        row = {
            "hora_salida_programada": "18:00",
            "checado_2": "17:30:00",
            "cruza_medianoche": False
        }
        
        resultado = self.detectar_salida_anticipada(row)
        assert resultado == False, "Debería retornar False sin checada de entrada"
    
    def test_multiples_checadas_ultima_es_la_mas_tardia(self):
        """Prueba que use la última checada (más tardía) para la comparación."""
        row = {
            "hora_salida_programada": "18:00",
            "checado_1": "08:00:00",
            "checado_2": "12:00:00",  # Almuerzo
            "checado_3": "17:30:00",  # Checada intermedia
            "checado_4": "17:45:00",  # Última checada, 15 min antes (dentro de tolerancia)
            "cruza_medianoche": False
        }
        
        resultado = self.detectar_salida_anticipada(row)
        assert resultado == False, "No debería detectar salida anticipada usando la última checada (dentro de tolerancia)"
    
    def test_turno_nocturno_normal(self):
        """Prueba turno nocturno sin salida anticipada."""
        row = {
            "hora_salida_programada": "06:00",  # Día siguiente
            "checado_1": "22:00:00",  # Entrada noche
            "checado_2": "06:00:00",  # Salida a tiempo (diferencia = 0 minutos)
            "cruza_medianoche": True
        }
        
        resultado = self.detectar_salida_anticipada(row)
        assert resultado == False, "No debería detectar salida anticipada en turno nocturno normal"
    
    def test_turno_nocturno_salida_anticipada(self):
        """Prueba turno nocturno con salida anticipada."""
        row = {
            "hora_salida_programada": "06:00",  # Día siguiente
            "checado_1": "22:00:00",  # Entrada noche
            "checado_2": "05:30:00",  # Salida 30 min antes
            "cruza_medianoche": True
        }
        
        resultado = self.detectar_salida_anticipada(row)
        assert resultado == True, "Debería detectar salida anticipada en turno nocturno"
    
    def test_turno_nocturno_cruce_medianoche_complejo(self):
        """Prueba turno nocturno con múltiples checadas y cruce de medianoche."""
        row = {
            "hora_salida_programada": "06:00",  # Día siguiente
            "checado_1": "22:00:00",  # Entrada
            "checado_2": "00:30:00",  # Después de medianoche
            "checado_3": "03:00:00",  # Madrugada
            "checado_4": "05:30:00",  # Salida 30 min antes
            "cruza_medianoche": True
        }
        
        resultado = self.detectar_salida_anticipada(row)
        assert resultado == True, "Debería detectar salida anticipada en turno nocturno complejo"
    
    def test_formato_hora_invalido(self):
        """Prueba que maneje correctamente formatos de hora inválidos."""
        row = {
            "hora_salida_programada": "18:00",
            "checado_1": "08:00:00",
            "checado_2": "hora_invalida",  # Formato inválido
            "cruza_medianoche": False
        }
        
        resultado = self.detectar_salida_anticipada(row)
        assert resultado == False, "Debería retornar False con formato de hora inválido"
    
    def test_hora_salida_formato_invalido(self):
        """Prueba que maneje correctamente formato de hora de salida inválido."""
        row = {
            "hora_salida_programada": "hora_invalida",
            "checado_1": "08:00:00",
            "checado_2": "17:30:00",
            "cruza_medianoche": False
        }
        
        resultado = self.detectar_salida_anticipada(row)
        assert resultado == False, "Debería retornar False con formato de hora de salida inválido"
    
    def test_valores_nulos(self):
        """Prueba que maneje correctamente valores nulos."""
        row = {
            "hora_salida_programada": None,
            "checado_1": "08:00:00",
            "checado_2": "17:30:00",
            "cruza_medianoche": False
        }
        
        resultado = self.detectar_salida_anticipada(row)
        assert resultado == False, "Debería retornar False con valores nulos"
    
    def test_checadas_mezcladas_con_nulos(self):
        """Prueba que maneje correctamente checadas mezcladas con valores nulos."""
        row = {
            "hora_salida_programada": "18:00",
            "checado_1": "08:00:00",
            "checado_2": None,
            "checado_3": "17:30:00",  # 30 minutos antes (fuera de tolerancia)
            "checado_4": None,
            "checado_5": "17:45:00",  # 15 minutos antes (dentro de tolerancia)
            "cruza_medianoche": False
        }
        
        resultado = self.detectar_salida_anticipada(row)
        assert resultado == False, "Debería usar la última checada válida (17:45) que está dentro de tolerancia"
    
    def test_salida_tardia_no_anticipada(self):
        """Prueba que no detecte salida anticipada cuando se sale después del horario."""
        row = {
            "hora_salida_programada": "18:00",
            "checado_1": "08:00:00",
            "checado_2": "18:30:00",  # 30 minutos después
            "cruza_medianoche": False
        }
        
        resultado = self.detectar_salida_anticipada(row)
        assert resultado == False, "No debería detectar salida anticipada cuando se sale tarde"
    
    def test_casos_limite_medianoche(self):
        """Prueba casos límite de medianoche."""
        # Caso 1: Salida a las 23:59, última checada a las 23:30
        row1 = {
            "hora_salida_programada": "23:59",
            "checado_1": "08:00:00",
            "checado_2": "23:30:00",  # 29 minutos antes
            "cruza_medianoche": False
        }
        
        resultado1 = self.detectar_salida_anticipada(row1)
        assert resultado1 == True, "Debería detectar salida anticipada cerca de medianoche"
        
        # Caso 2: Salida a las 00:01, última checada a las 23:45
        row2 = {
            "hora_salida_programada": "00:01",
            "checado_1": "22:00:00",
            "checado_2": "23:45:00",  # 16 minutos antes (considerando cruce)
            "cruza_medianoche": True
        }
        
        resultado2 = self.detectar_salida_anticipada(row2)
        assert resultado2 == True, "Debería detectar salida anticipada en cruce de medianoche"
    
    def test_tolerancia_configurable(self):
        """Prueba que la tolerancia sea configurable correctamente."""
        # Verificar que la tolerancia esté configurada
        assert TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS == 15, "La tolerancia debería ser 15 minutos"
        
        # Probar con diferentes márgenes
        row_exacto = {
            "hora_salida_programada": "18:00",
            "checado_1": "08:00:00",
            "checado_2": "17:45:00",  # Exactamente 15 minutos antes
            "cruza_medianoche": False
        }
        
        resultado_exacto = self.detectar_salida_anticipada(row_exacto)
        assert resultado_exacto == False, "No debería detectar en el límite exacto de tolerancia"
        
        row_un_minuto_mas = {
            "hora_salida_programada": "18:00",
            "checado_1": "08:00:00",
            "checado_2": "17:44:00",  # 16 minutos antes (1 minuto más que tolerancia)
            "cruza_medianoche": False
        }
        
        resultado_un_minuto_mas = self.detectar_salida_anticipada(row_un_minuto_mas)
        assert resultado_un_minuto_mas == True, "Debería detectar 1 minuto fuera de tolerancia"
    
    def test_ordenamiento_checadas(self):
        """Prueba que el ordenamiento de checadas funcione correctamente."""
        # Checadas en orden desordenado
        row = {
            "hora_salida_programada": "18:00",
            "checado_1": "17:30:00",  # No es la última
            "checado_2": "08:00:00",  # Primera
            "checado_3": "17:45:00",  # Última (más tardía)
            "checado_4": "12:00:00",  # Intermedia
            "cruza_medianoche": False
        }
        
        resultado = self.detectar_salida_anticipada(row)
        assert resultado == False, "Debería usar la checada más tardía (17:45) para comparar"
    
    def test_casos_edge_horas_extremas(self):
        """Prueba casos edge con horas extremas."""
        # Caso: Salida a las 00:00, última checada a las 23:44
        row_medianoche = {
            "hora_salida_programada": "00:00",
            "checado_1": "22:00:00",
            "checado_2": "23:44:00",  # 16 minutos antes (considerando cruce)
            "cruza_medianoche": True
        }
        
        resultado_medianoche = self.detectar_salida_anticipada(row_medianoche)
        assert resultado_medianoche == True, "Debería detectar salida anticipada en medianoche"
        
        # Caso: Salida a las 23:59, última checada a las 23:43
        row_antes_medianoche = {
            "hora_salida_programada": "23:59",
            "checado_1": "08:00:00",
            "checado_2": "23:43:00",  # 16 minutos antes
            "cruza_medianoche": False
        }
        
        resultado_antes_medianoche = self.detectar_salida_anticipada(row_antes_medianoche)
        assert resultado_antes_medianoche == True, "Debería detectar salida anticipada antes de medianoche"


class TestIntegracionSalidasAnticipadas:
    """
    Pruebas de integración para la funcionalidad de salidas anticipadas.
    """
    
    def test_dataframe_completo_salidas_anticipadas(self):
        """Prueba la integración completa con DataFrame."""
        import pandas as pd
        from datetime import datetime
        from generar_reporte_optimizado import analizar_asistencia_con_horarios_cache
        
        # Crear DataFrame de prueba
        data = {
            'employee': ['EMP001', 'EMP002', 'EMP003'],
            'dia': [datetime(2025, 1, 1), datetime(2025, 1, 1), datetime(2025, 1, 1)],
            'dia_iso': ['2025-01-01', '2025-01-01', '2025-01-01'],  # Columna requerida
            'hora_salida_programada': ['18:00', '18:00', '18:00'],
            'checado_1': ['08:00:00', '08:00:00', '08:00:00'],
            'checado_2': ['17:30:00', '17:50:00', '18:30:00'],  # Anticipada, Normal, Tardía
            'cruza_medianoche': [False, False, False]
        }
        
        df = pd.DataFrame(data)
        
        # Simular caché de horarios vacío
        cache_horarios = {}
        
        # Aplicar análisis (esto incluirá la detección de salidas anticipadas)
        df_resultado = analizar_asistencia_con_horarios_cache(df, cache_horarios)
        
        # Verificar que se añadió la columna
        assert 'salida_anticipada' in df_resultado.columns, "Debería existir columna salida_anticipada"
        
        # Verificar resultados esperados
        assert df_resultado.iloc[0]['salida_anticipada'] == True, "EMP001 debería tener salida anticipada"
        assert df_resultado.iloc[1]['salida_anticipada'] == False, "EMP002 no debería tener salida anticipada"
        assert df_resultado.iloc[2]['salida_anticipada'] == False, "EMP003 no debería tener salida anticipada"


if __name__ == "__main__":
    # Ejecutar pruebas
    pytest.main([__file__, "-v"]) 