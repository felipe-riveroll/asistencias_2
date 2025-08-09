"""
Tests unitarios para el módulo reporte_excel.py
Enfocado en la lógica de coloreado de checadas
"""

import pytest
import pandas as pd
from datetime import datetime, date, timedelta
from reporte_excel import GeneradorReporteExcel
from db_postgres_connection import obtener_horario_empleado
from config import TOLERANCIA_RETARDO_MINUTOS, UMBRAL_FALTA_INJUSTIFICADA_MINUTOS


def crear_datos_prueba():
    """Crear datos de prueba con horarios programados y tipos de retardo calculados"""
    # Mock de cache de horarios con diferentes empleados y horarios
    cache_horarios = {
        "EMP001": {
            True: {  # Primera quincena
                1: {"hora_entrada": "08:00:00", "hora_salida": "16:00:00", "horas_totales": 8, "cruza_medianoche": False},  # Lunes
                2: {"hora_entrada": "09:00:00", "hora_salida": "17:00:00", "horas_totales": 8, "cruza_medianoche": False},  # Martes
                3: {"hora_entrada": "07:30:00", "hora_salida": "15:30:00", "horas_totales": 8, "cruza_medianoche": False},  # Miércoles
            },
            False: {  # Segunda quincena
                1: {"hora_entrada": "08:00:00", "hora_salida": "16:00:00", "horas_totales": 8, "cruza_medianoche": False},
            }
        },
        "EMP002": {
            True: {
                1: {"hora_entrada": "06:00:00", "hora_salida": "14:00:00", "horas_totales": 8, "cruza_medianoche": False},  # Lunes
            }
        }
    }
    
    def calcular_tipo_retardo(hora_programada, hora_checada):
        """Calcular tipo de retardo basado en los umbrales configurados"""
        if not hora_programada or not hora_checada:
            return "A Tiempo"
            
        try:
            # Convertir a datetime para calcular diferencia
            fecha_base = "2023-01-01"
            dt_programada = datetime.combine(datetime.strptime(fecha_base, "%Y-%m-%d").date(), 
                                           datetime.strptime(hora_programada, "%H:%M:%S").time())
            dt_checada = datetime.combine(datetime.strptime(fecha_base, "%Y-%m-%d").date(),
                                        datetime.strptime(hora_checada, "%H:%M:%S").time())
            
            diferencia_minutos = (dt_checada - dt_programada).total_seconds() / 60
            
            if diferencia_minutos <= TOLERANCIA_RETARDO_MINUTOS:
                return "A Tiempo"
            elif diferencia_minutos <= UMBRAL_FALTA_INJUSTIFICADA_MINUTOS:
                return "Retardo"
            else:
                return "Falta Injustificada"
        except Exception:
            return "A Tiempo"
    
    # Casos de prueba con diferentes escenarios
    casos_prueba = [
        {
            "employee": "EMP001",
            "dia_semana": 1,  # Lunes
            "es_primera_quincena": True,
            "checado_1": "08:03:00",  # 3 min tarde - A Tiempo
            "descripcion": "A Tiempo"
        },
        {
            "employee": "EMP001",
            "dia_semana": 2,  # Martes
            "es_primera_quincena": True,
            "checado_1": "09:30:00",  # 30 min tarde - Retardo
            "descripcion": "Retardo"
        },
        {
            "employee": "EMP001",
            "dia_semana": 3,  # Miércoles  
            "es_primera_quincena": True,
            "checado_1": "08:31:00",  # 61 min tarde (programada 07:30) - Falta Injustificada
            "descripcion": "Falta Injustificada"
        },
        {
            "employee": "EMP002",
            "dia_semana": 1,  # Lunes
            "es_primera_quincena": True,
            "checado_1": "06:45:00",  # 45 min tarde - Retardo
            "descripcion": "Retardo"
        }
    ]
    
    # Enriquecer casos con datos calculados
    for caso in casos_prueba:
        horario = obtener_horario_empleado(
            caso["employee"], 
            caso["dia_semana"], 
            caso["es_primera_quincena"], 
            cache_horarios
        )
        
        if horario:
            caso["hora_entrada_programada"] = horario["hora_entrada"]
            caso["tipo_retardo"] = calcular_tipo_retardo(
                horario["hora_entrada"], 
                caso["checado_1"]
            )
        else:
            caso["hora_entrada_programada"] = "08:00:00"  # Fallback
            caso["tipo_retardo"] = "A Tiempo"
    
    return casos_prueba, cache_horarios


class TestColoreadoChecadas:
    """Tests para la lógica de coloreado de checadas"""
    
    def setup_method(self):
        """Configurar el generador para cada test"""
        self.generador = GeneradorReporteExcel()
        
        # Crear fills de prueba
        self.fill_amarillo = "FFFF00"  # Simular PatternFill
        self.fill_rojo = "FF0000"      # Simular PatternFill
        self.fill_verde = "92D050"     # Simular PatternFill
        self.fill_verde_entrada_nocturno = "70AD47"  # Simular PatternFill
        
        # Mock cell para testing
        self.mock_cell = type('MockCell', (), {
            'fill': None,
            'font': type('MockFont', (), {'color': None})()
        })()
        
        # Resetear el mock antes de cada test
        self.mock_cell.fill = None
        self.mock_cell.font.color = None
        
        # Cargar datos de prueba
        self.casos_prueba, self.cache_horarios = crear_datos_prueba()
    
    def test_entrada_a_tiempo_sin_color(self):
        """Test: Entrada a tiempo no debe tener color"""
        # Buscar caso de A Tiempo en datos de prueba
        caso_a_tiempo = next(c for c in self.casos_prueba if c["descripcion"] == "A Tiempo")
        
        self.generador._aplicar_color_checada(
            self.mock_cell,
            caso_a_tiempo["checado_1"],
            True,  # es_entrada
            False,  # retardo_perdonado
            caso_a_tiempo["tipo_retardo"],
            caso_a_tiempo["hora_entrada_programada"],
            self.fill_amarillo,
            self.fill_rojo,
            self.fill_verde,
            self.fill_verde_entrada_nocturno
        )
        
        assert self.mock_cell.fill is None
    
    def test_retardo_amarillo(self):
        """Test: Retardo debe ser amarillo"""
        # Buscar caso de Retardo en datos de prueba
        caso_retardo = next(c for c in self.casos_prueba if c["descripcion"] == "Retardo")
        
        self.generador._aplicar_color_checada(
            self.mock_cell,
            caso_retardo["checado_1"],
            True,  # es_entrada
            False,  # retardo_perdonado
            caso_retardo["tipo_retardo"],
            caso_retardo["hora_entrada_programada"],
            self.fill_amarillo,
            self.fill_rojo,
            self.fill_verde,
            self.fill_verde_entrada_nocturno
        )
        
        assert self.mock_cell.fill == self.fill_amarillo
    
    def test_falta_injustificada_rojo(self):
        """Test: Falta Injustificada (>60 min tarde) debe ser rojo"""
        # Buscar caso de Falta Injustificada en datos de prueba
        caso_falta = next(c for c in self.casos_prueba if c["descripcion"] == "Falta Injustificada")
        
        self.generador._aplicar_color_checada(
            self.mock_cell,
            caso_falta["checado_1"],
            True,  # es_entrada
            False,  # retardo_perdonado
            caso_falta["tipo_retardo"],
            caso_falta["hora_entrada_programada"],
            self.fill_amarillo,
            self.fill_rojo,
            self.fill_verde,
            self.fill_verde_entrada_nocturno
        )
        
        assert self.mock_cell.fill == self.fill_rojo
        # Verificar que el color del texto es blanco (puede ser un objeto Color o string)
        assert self.mock_cell.font.color is not None
    
    def test_retardo_perdonado_sin_color(self):
        """Test: Retardo perdonado no debe tener color"""
        # Hora programada: 08:00:00, entrada: 08:15:00 (retardo) pero perdonado
        self.generador._aplicar_color_checada(
            self.mock_cell,
            "08:15:00",
            True,  # es_entrada
            True,   # retardo_perdonado
            "Retardo",
            "08:00:00",  # hora_programada
            self.fill_amarillo,
            self.fill_rojo,
            self.fill_verde,
            self.fill_verde_entrada_nocturno
        )
        
        assert self.mock_cell.fill is None
    
    def test_checada_no_entrada_sin_color(self):
        """Test: Checadas 2-5 no deben tener color"""
        # Checada 2 (no es entrada)
        self.generador._aplicar_color_checada(
            self.mock_cell,
            "12:00:00",
            False,  # es_entrada (checada 2-5)
            False,  # retardo_perdonado
            "A Tiempo",
            "08:00:00",  # hora_programada
            self.fill_amarillo,
            self.fill_rojo,
            self.fill_verde,
            self.fill_verde_entrada_nocturno
        )
        
        assert self.mock_cell.fill is None
    
    def test_checada_vacia_sin_color(self):
        """Test: Checada vacía no debe tener color"""
        self.generador._aplicar_color_checada(
            self.mock_cell,
            "",  # checada vacía
            True,  # es_entrada
            False,  # retardo_perdonado
            "A Tiempo",
            "08:00:00",  # hora_programada
            self.fill_amarillo,
            self.fill_rojo,
            self.fill_verde,
            self.fill_verde_entrada_nocturno
        )
        
        assert self.mock_cell.fill is None
    
    def test_falta_entrada_nocturno_verde(self):
        """Test: Falta entrada nocturno debe ser verde en celda vacía"""
        self.generador._aplicar_color_checada(
            self.mock_cell,
            "",  # checada vacía
            True,  # es_entrada
            False,  # retardo_perdonado
            "Falta Entrada Nocturno",
            "08:00:00",  # hora_programada
            self.fill_amarillo,
            self.fill_rojo,
            self.fill_verde,
            self.fill_verde_entrada_nocturno
        )
        
        assert self.mock_cell.fill == self.fill_verde_entrada_nocturno
    
    def test_horarios_dinamicos_diferentes_empleados(self):
        """Test: Lógica funciona con diferentes horarios por empleado"""
        # Probar todos los casos de retardo para verificar cálculos dinámicos
        casos_retardo = [c for c in self.casos_prueba if c["descripcion"] == "Retardo"]
        
        for caso in casos_retardo:
            # Resetear cell
            self.mock_cell.fill = None
            self.mock_cell.font.color = None
            
            self.generador._aplicar_color_checada(
                self.mock_cell,
                caso["checado_1"],
                True,  # es_entrada
                False,  # retardo_perdonado
                caso["tipo_retardo"],
                caso["hora_entrada_programada"],
                self.fill_amarillo,
                self.fill_rojo,
                self.fill_verde,
                self.fill_verde_entrada_nocturno
            )
            
            assert self.mock_cell.fill == self.fill_amarillo, f"Falló para empleado {caso['employee']} con horario {caso['hora_entrada_programada']}"
    
    def test_sin_hora_programada_sin_color(self):
        """Test: Sin hora programada no debe tener color"""
        # Sin hora programada, no debe aplicar color
        self.generador._aplicar_color_checada(
            self.mock_cell,
            "08:15:00",
            True,  # es_entrada
            False,  # retardo_perdonado
            "Retardo",
            None,  # hora_programada
            self.fill_amarillo,
            self.fill_rojo,
            self.fill_verde,
            self.fill_verde_entrada_nocturno
        )
        
        # Con la nueva lógica, sin hora programada no debe aplicar color
        assert self.mock_cell.fill is None
    
    def test_solo_retardo_amarillo_falta_injustificada_rojo(self):
        """Test: Solo 'Retardo' debe ser amarillo y solo 'Falta Injustificada' debe ser rojo"""
        # Verificar que solo los casos de "Retardo" reciben color amarillo
        casos_retardo = [c for c in self.casos_prueba if c["descripcion"] == "Retardo"]
        for caso in casos_retardo:
            self.mock_cell.fill = None
            self.mock_cell.font.color = None
            
            self.generador._aplicar_color_checada(
                self.mock_cell,
                caso["checado_1"],
                True,
                False,
                caso["tipo_retardo"],
                caso["hora_entrada_programada"],
                self.fill_amarillo,
                self.fill_rojo,
                self.fill_verde,
                self.fill_verde_entrada_nocturno
            )
            
            assert self.mock_cell.fill == self.fill_amarillo, f"Retardo debe ser amarillo para {caso['employee']}"
        
        # Verificar que solo los casos de "Falta Injustificada" reciben color rojo
        casos_falta = [c for c in self.casos_prueba if c["descripcion"] == "Falta Injustificada"]
        for caso in casos_falta:
            self.mock_cell.fill = None
            self.mock_cell.font.color = None
            
            self.generador._aplicar_color_checada(
                self.mock_cell,
                caso["checado_1"],
                True,
                False,
                caso["tipo_retardo"],
                caso["hora_entrada_programada"],
                self.fill_amarillo,
                self.fill_rojo,
                self.fill_verde,
                self.fill_verde_entrada_nocturno
            )
            
            assert self.mock_cell.fill == self.fill_rojo, f"Falta Injustificada debe ser rojo para {caso['employee']}"
            assert self.mock_cell.font.color is not None, f"Falta Injustificada debe tener texto blanco para {caso['employee']}"
        
        # Verificar que los casos "A Tiempo" no reciben color
        casos_a_tiempo = [c for c in self.casos_prueba if c["descripcion"] == "A Tiempo"]
        for caso in casos_a_tiempo:
            self.mock_cell.fill = None
            self.mock_cell.font.color = None
            
            self.generador._aplicar_color_checada(
                self.mock_cell,
                caso["checado_1"],
                True,
                False,
                caso["tipo_retardo"],
                caso["hora_entrada_programada"],
                self.fill_amarillo,
                self.fill_rojo,
                self.fill_verde,
                self.fill_verde_entrada_nocturno
            )
            
            assert self.mock_cell.fill is None, f"A Tiempo no debe tener color para {caso['employee']}"


if __name__ == "__main__":
    # Ejecutar tests
    pytest.main([__file__, "-v"])
