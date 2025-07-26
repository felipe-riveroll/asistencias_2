"""
Pruebas unitarias para la integración de permisos ERPNext.
Incluye todos los casos de prueba especificados para validar
el comportamiento correcto de la funcionalidad de permisos.
"""

import pytest
import pandas as pd
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, MagicMock
import requests
import json

# Importar las funciones a probar
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generar_reporte_optimizado import (
    fetch_leave_applications,
    procesar_permisos_empleados,
    ajustar_horas_esperadas_con_permisos,
    clasificar_faltas_con_permisos
)


class TestFetchLeaveApplications:
    """Pruebas para la función de obtención de permisos de la API"""
    
    @patch('generar_reporte_optimizado.requests.get')
    @patch('generar_reporte_optimizado.API_KEY', 'test_key')
    @patch('generar_reporte_optimizado.API_SECRET', 'test_secret')
    def test_respuesta_vacia_api(self, mock_get):
        """Caso 7: Respuesta vacía de la API"""
        # Configurar mock para respuesta vacía
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = fetch_leave_applications("2025-07-16", "2025-07-23")
        
        assert result == []
        assert mock_get.called
        
    @patch('generar_reporte_optimizado.requests.get')
    def test_error_conexion_api(self, mock_get):
        """Caso 6: Error de conexión a API ERPNext"""
        # Configurar mock para simular error de conexión
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        result = fetch_leave_applications("2025-07-16", "2025-07-23")
        
        assert result == []
        
    @patch('generar_reporte_optimizado.requests.get')
    @patch('generar_reporte_optimizado.API_KEY', 'test_key')
    @patch('generar_reporte_optimizado.API_SECRET', 'test_secret')
    def test_timeout_api_con_reintento(self, mock_get):
        """Caso 6: Timeout de API con reintento automático"""
        # Primera llamada: timeout, segunda llamada: éxito
        mock_response_success = Mock()
        mock_response_success.json.return_value = {
            "data": [{
                "employee": "1",
                "employee_name": "Test Employee",
                "leave_type": "Vacaciones",
                "from_date": "2025-07-16",
                "to_date": "2025-07-16",
                "status": "Approved"
            }]
        }
        mock_response_success.raise_for_status.return_value = None
        
        mock_get.side_effect = [
            requests.exceptions.Timeout("Request timed out"),
            mock_response_success
        ]
        
        result = fetch_leave_applications("2025-07-16", "2025-07-23")
        
        assert len(result) == 1
        assert result[0]["employee"] == "1"
        assert mock_get.call_count == 2


class TestProcesarPermisosEmpleados:
    """Pruebas para el procesamiento de permisos por empleado"""
    
    def test_empleado_sin_permisos(self):
        """Caso 3: Empleado sin permisos en el período"""
        leave_data = []
        
        result = procesar_permisos_empleados(leave_data)
        
        assert result == {}
        
    def test_empleado_permiso_un_dia(self):
        """Caso 1: Empleado con permiso de un día"""
        leave_data = [{
            "employee": "25",
            "employee_name": "Karla Ivette Chimal Moreno",
            "leave_type": "Incapacidad por enfermedad",
            "from_date": "2025-07-16",
            "to_date": "2025-07-16",
            "status": "Approved"
        }]
        
        result = procesar_permisos_empleados(leave_data)
        
        assert "25" in result
        assert date(2025, 7, 16) in result["25"]
        assert result["25"][date(2025, 7, 16)]["leave_type"] == "Incapacidad por enfermedad"
        assert result["25"][date(2025, 7, 16)]["employee_name"] == "Karla Ivette Chimal Moreno"
        
    def test_empleado_permiso_multiples_dias(self):
        """Caso 2: Empleado con permiso de múltiples días"""
        leave_data = [{
            "employee": "47",
            "employee_name": "Maria Brenda Bautista Zavala",
            "leave_type": "Vacaciones (después de 4 años)",
            "from_date": "2025-07-11",
            "to_date": "2025-07-14",
            "status": "Approved"
        }]
        
        result = procesar_permisos_empleados(leave_data)
        
        assert "47" in result
        # Verificar que todos los días del rango están incluidos
        expected_dates = [
            date(2025, 7, 11),
            date(2025, 7, 12),
            date(2025, 7, 13),
            date(2025, 7, 14)
        ]
        
        for expected_date in expected_dates:
            assert expected_date in result["47"]
            assert result["47"][expected_date]["leave_type"] == "Vacaciones (después de 4 años)"
            
    def test_permiso_abarca_fin_semana(self):
        """Caso 4: Permiso que abarca fin de semana"""
        leave_data = [{
            "employee": "65",
            "employee_name": "Marisol Rivera Martínez",
            "leave_type": "Vacaciones (después de 2 años)",
            "from_date": "2025-07-12",  # Viernes
            "to_date": "2025-07-15",    # Lunes
            "status": "Approved"
        }]
        
        result = procesar_permisos_empleados(leave_data)
        
        assert "65" in result
        # Verificar que incluye fin de semana
        expected_dates = [
            date(2025, 7, 12),  # Viernes
            date(2025, 7, 13),  # Sábado
            date(2025, 7, 14),  # Domingo
            date(2025, 7, 15)   # Lunes
        ]
        
        for expected_date in expected_dates:
            assert expected_date in result["65"]
            
    def test_multiples_permisos_mismo_periodo(self):
        """Caso 5: Múltiples permisos en el mismo período"""
        leave_data = [
            {
                "employee": "47",
                "employee_name": "Maria Brenda Bautista Zavala",
                "leave_type": "Vacaciones (después de 4 años)",
                "from_date": "2025-07-09",
                "to_date": "2025-07-09",
                "status": "Approved"
            },
            {
                "employee": "47",
                "employee_name": "Maria Brenda Bautista Zavala",
                "leave_type": "Permiso sin goce de sueldo",
                "from_date": "2025-07-10",
                "to_date": "2025-07-10",
                "status": "Approved"
            },
            {
                "employee": "47",
                "employee_name": "Maria Brenda Bautista Zavala",
                "leave_type": "Vacaciones (después de 4 años)",
                "from_date": "2025-07-11",
                "to_date": "2025-07-14",
                "status": "Approved"
            }
        ]
        
        result = procesar_permisos_empleados(leave_data)
        
        assert "47" in result
        # Verificar que tiene permisos en múltiples días
        assert date(2025, 7, 9) in result["47"]
        assert date(2025, 7, 10) in result["47"]
        assert date(2025, 7, 11) in result["47"]
        assert date(2025, 7, 12) in result["47"]
        assert date(2025, 7, 13) in result["47"]
        assert date(2025, 7, 14) in result["47"]
        
        # Verificar tipos de permiso específicos
        assert result["47"][date(2025, 7, 9)]["leave_type"] == "Vacaciones (después de 4 años)"
        assert result["47"][date(2025, 7, 10)]["leave_type"] == "Permiso sin goce de sueldo"
        assert result["47"][date(2025, 7, 11)]["leave_type"] == "Vacaciones (después de 4 años)"


class TestAjustarHorasEsperadasConPermisos:
    """Pruebas para el ajuste de horas esperadas con permisos"""
    
    def setup_method(self):
        """Configuración inicial para cada test"""
        self.df_base = pd.DataFrame({
            'employee': ['1', '1', '1', '25', '25'],
            'dia': [
                date(2025, 7, 16),
                date(2025, 7, 17),
                date(2025, 7, 18),
                date(2025, 7, 16),
                date(2025, 7, 17)
            ],
            'horas_esperadas': ['9:00:00', '9:00:00', '9:00:00', '8:00:00', '8:00:00'],
            'tipo_retardo': ['A Tiempo', 'A Tiempo', 'Falta', 'A Tiempo', 'Falta']
        })
        
        self.cache_horarios = {
            '1': {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None},
            '25': {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None}
        }
        
    def test_sin_permisos(self):
        """Caso 3: Empleado sin permisos en el período"""
        permisos_dict = {}
        
        result = ajustar_horas_esperadas_con_permisos(
            self.df_base.copy(), permisos_dict, self.cache_horarios
        )
        
        # Verificar que no se realizaron ajustes
        assert (result['tiene_permiso'] == False).all()
        assert (result['horas_esperadas'] == result['horas_esperadas_originales']).all()
        assert (result['horas_descontadas_permiso'] == '00:00:00').all()
        
    def test_permiso_un_dia(self):
        """Caso 1: Empleado con permiso de un día"""
        permisos_dict = {
            '25': {
                date(2025, 7, 16): {
                    'leave_type': 'Incapacidad por enfermedad',
                    'employee_name': 'Karla Ivette Chimal Moreno',
                    'from_date': date(2025, 7, 16),
                    'to_date': date(2025, 7, 16),
                    'status': 'Approved'
                }
            }
        }
        
        result = ajustar_horas_esperadas_con_permisos(
            self.df_base.copy(), permisos_dict, self.cache_horarios
        )
        
        # Verificar empleado 25 en día 16/07
        emp25_dia16 = result[(result['employee'] == '25') & (result['dia'] == date(2025, 7, 16))]
        assert len(emp25_dia16) == 1
        assert emp25_dia16.iloc[0]['tiene_permiso'] == True
        assert emp25_dia16.iloc[0]['tipo_permiso'] == 'Incapacidad por enfermedad'
        assert emp25_dia16.iloc[0]['horas_esperadas'] == '00:00:00'
        assert emp25_dia16.iloc[0]['horas_descontadas_permiso'] == '8:00:00'
        
        # Verificar que otros días no se afectaron
        emp25_dia17 = result[(result['employee'] == '25') & (result['dia'] == date(2025, 7, 17))]
        assert emp25_dia17.iloc[0]['tiene_permiso'] == False
        assert emp25_dia17.iloc[0]['horas_esperadas'] == '8:00:00'
        
    def test_permiso_multiples_dias(self):
        """Caso 2: Empleado con permiso de múltiples días"""
        permisos_dict = {
            '1': {
                date(2025, 7, 17): {
                    'leave_type': 'Vacaciones',
                    'employee_name': 'Test Employee',
                    'from_date': date(2025, 7, 17),
                    'to_date': date(2025, 7, 18),
                    'status': 'Approved'
                },
                date(2025, 7, 18): {
                    'leave_type': 'Vacaciones',
                    'employee_name': 'Test Employee',
                    'from_date': date(2025, 7, 17),
                    'to_date': date(2025, 7, 18),
                    'status': 'Approved'
                }
            }
        }
        
        result = ajustar_horas_esperadas_con_permisos(
            self.df_base.copy(), permisos_dict, self.cache_horarios
        )
        
        # Verificar ambos días con permiso
        emp1_dias_permiso = result[
            (result['employee'] == '1') & 
            (result['dia'].isin([date(2025, 7, 17), date(2025, 7, 18)]))
        ]
        
        assert len(emp1_dias_permiso) == 2
        assert (emp1_dias_permiso['tiene_permiso'] == True).all()
        assert (emp1_dias_permiso['horas_esperadas'] == '00:00:00').all()
        assert (emp1_dias_permiso['horas_descontadas_permiso'] == '9:00:00').all()
        
        # Verificar día sin permiso
        emp1_sin_permiso = result[(result['employee'] == '1') & (result['dia'] == date(2025, 7, 16))]
        assert emp1_sin_permiso.iloc[0]['tiene_permiso'] == False


class TestClasificarFaltasConPermisos:
    """Pruebas para la reclasificación de faltas con permisos"""
    
    def setup_method(self):
        """Configuración inicial para cada test"""
        self.df_base = pd.DataFrame({
            'employee': ['1', '1', '25', '25'],
            'dia': [
                date(2025, 7, 16),
                date(2025, 7, 17),
                date(2025, 7, 16),
                date(2025, 7, 17)
            ],
            'tipo_retardo': ['A Tiempo', 'Falta', 'Falta', 'A Tiempo'],
            'tiene_permiso': [False, True, True, False],
            'tipo_permiso': [None, 'Vacaciones', 'Incapacidad', None],
            'es_falta': [0, 1, 1, 0]
        })
        
    def test_faltas_justificadas_con_permisos(self):
        """Verificar que las faltas se justifican correctamente con permisos"""
        result = clasificar_faltas_con_permisos(self.df_base.copy())
        
        # Verificar empleado 1, día 17 (falta con permiso)
        emp1_dia17 = result[(result['employee'] == '1') & (result['dia'] == date(2025, 7, 17))]
        assert len(emp1_dia17) == 1
        assert emp1_dia17.iloc[0]['tipo_falta_ajustada'] == 'Falta Justificada'
        assert emp1_dia17.iloc[0]['falta_justificada'] == True
        assert emp1_dia17.iloc[0]['es_falta_ajustada'] == 0  # No cuenta como falta
        
        # Verificar empleado 25, día 16 (falta con permiso)
        emp25_dia16 = result[(result['employee'] == '25') & (result['dia'] == date(2025, 7, 16))]
        assert emp25_dia16.iloc[0]['tipo_falta_ajustada'] == 'Falta Justificada'
        assert emp25_dia16.iloc[0]['falta_justificada'] == True
        assert emp25_dia16.iloc[0]['es_falta_ajustada'] == 0
        
        # Verificar que días sin permiso mantienen clasificación original
        emp1_dia16 = result[(result['employee'] == '1') & (result['dia'] == date(2025, 7, 16))]
        assert emp1_dia16.iloc[0]['tipo_falta_ajustada'] == 'A Tiempo'
        assert emp1_dia16.iloc[0]['falta_justificada'] == False
        
    def test_sin_faltas_para_justificar(self):
        """Verificar comportamiento cuando no hay faltas que justificar"""
        df_sin_faltas_permiso = pd.DataFrame({
            'employee': ['1', '1'],
            'dia': [date(2025, 7, 16), date(2025, 7, 17)],
            'tipo_retardo': ['A Tiempo', 'A Tiempo'],
            'tiene_permiso': [True, False],
            'tipo_permiso': ['Vacaciones', None],
            'es_falta': [0, 0]
        })
        
        result = clasificar_faltas_con_permisos(df_sin_faltas_permiso)
        
        # Verificar que no se justificaron faltas
        assert (result['falta_justificada'] == False).all()
        assert (result['es_falta_ajustada'] == result['es_falta']).all()


class TestIntegracionCompleta:
    """Pruebas de integración para el flujo completo de permisos"""
    
    def test_flujo_completo_con_permisos(self):
        """Prueba del flujo completo desde permisos hasta ajuste final"""
        # Datos de permisos de la API
        leave_data = [
            {
                "employee": "1",
                "employee_name": "Test Employee 1",
                "leave_type": "Vacaciones",
                "from_date": "2025-07-16",
                "to_date": "2025-07-17",
                "status": "Approved"
            },
            {
                "employee": "2",
                "employee_name": "Test Employee 2",
                "leave_type": "Incapacidad",
                "from_date": "2025-07-16",
                "to_date": "2025-07-16",
                "status": "Approved"
            }
        ]
        
        # DataFrame inicial de asistencia
        df_asistencia = pd.DataFrame({
            'employee': ['1', '1', '1', '2', '2', '2'],
            'dia': [
                date(2025, 7, 16), date(2025, 7, 17), date(2025, 7, 18),
                date(2025, 7, 16), date(2025, 7, 17), date(2025, 7, 18)
            ],
            'horas_esperadas': ['8:00:00', '8:00:00', '8:00:00', '8:00:00', '8:00:00', '8:00:00'],
            'tipo_retardo': ['A Tiempo', 'Falta', 'A Tiempo', 'Falta', 'A Tiempo', 'Retardo'],
            'es_falta': [0, 1, 0, 1, 0, 0]
        })
        
        cache_horarios = {
            '1': {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None},
            '2': {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None}
        }
        
        # Paso 1: Procesar permisos
        permisos_dict = procesar_permisos_empleados(leave_data)
        
        # Paso 2: Ajustar horas esperadas
        df_con_permisos = ajustar_horas_esperadas_con_permisos(
            df_asistencia.copy(), permisos_dict, cache_horarios
        )
        
        # Paso 3: Clasificar faltas
        df_final = clasificar_faltas_con_permisos(df_con_permisos)
        
        # Verificaciones finales
        # Empleado 1 - días con permiso
        emp1_permiso = df_final[
            (df_final['employee'] == '1') & 
            (df_final['dia'].isin([date(2025, 7, 16), date(2025, 7, 17)]))
        ]
        assert len(emp1_permiso) == 2
        assert (emp1_permiso['tiene_permiso'] == True).all()
        assert (emp1_permiso['horas_esperadas'] == '00:00:00').all()
        
        # Verificar que la falta del día 17 se justificó
        emp1_dia17 = df_final[(df_final['employee'] == '1') & (df_final['dia'] == date(2025, 7, 17))]
        assert emp1_dia17.iloc[0]['falta_justificada'] == True
        assert emp1_dia17.iloc[0]['tipo_falta_ajustada'] == 'Falta Justificada'
        
        # Empleado 2 - día con permiso
        emp2_dia16 = df_final[(df_final['employee'] == '2') & (df_final['dia'] == date(2025, 7, 16))]
        assert emp2_dia16.iloc[0]['tiene_permiso'] == True
        assert emp2_dia16.iloc[0]['falta_justificada'] == True
        assert emp2_dia16.iloc[0]['horas_esperadas'] == '00:00:00'
        
        # Empleado 2 - días sin permiso
        emp2_sin_permiso = df_final[
            (df_final['employee'] == '2') & 
            (df_final['dia'].isin([date(2025, 7, 17), date(2025, 7, 18)]))
        ]
        assert (emp2_sin_permiso['tiene_permiso'] == False).all()
        assert (emp2_sin_permiso['horas_esperadas'] == '8:00:00').all()


class TestCasosEspeciales:
    """Pruebas para casos especiales y edge cases"""
    
    def test_dataframe_vacio(self):
        """Verificar manejo de DataFrame vacío"""
        df_vacio = pd.DataFrame()
        permisos_dict = {}
        cache_horarios = {}
        
        result_ajuste = ajustar_horas_esperadas_con_permisos(df_vacio, permisos_dict, cache_horarios)
        result_clasificacion = clasificar_faltas_con_permisos(df_vacio)
        
        assert result_ajuste.empty
        assert result_clasificacion.empty
        
    def test_permiso_con_horas_esperadas_cero(self):
        """Verificar comportamiento con horas esperadas en 00:00:00"""
        df_test = pd.DataFrame({
            'employee': ['1'],
            'dia': [date(2025, 7, 16)],
            'horas_esperadas': ['00:00:00'],
            'tipo_retardo': ['Día no Laborable']
        })
        
        permisos_dict = {
            '1': {
                date(2025, 7, 16): {
                    'leave_type': 'Vacaciones',
                    'employee_name': 'Test Employee',
                    'from_date': date(2025, 7, 16),
                    'to_date': date(2025, 7, 16),
                    'status': 'Approved'
                }
            }
        }
        
        cache_horarios = {'1': {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None}}
        
        result = ajustar_horas_esperadas_con_permisos(df_test, permisos_dict, cache_horarios)
        
        # Verificar que se marca el permiso pero no se descuentan horas (ya eran 0)
        assert result.iloc[0]['tiene_permiso'] == True
        assert result.iloc[0]['horas_esperadas'] == '00:00:00'
        assert result.iloc[0]['horas_descontadas_permiso'] == '00:00:00'
        
    def test_multiples_empleados_con_permisos_complejos(self):
        """Prueba con múltiples empleados y permisos complejos"""
        leave_data = [
            # Empleado con permiso de un día
            {
                "employee": "1",
                "employee_name": "Employee 1",
                "leave_type": "Vacaciones",
                "from_date": "2025-07-16",
                "to_date": "2025-07-16",
                "status": "Approved"
            },
            # Empleado con permisos múltiples días no consecutivos
            {
                "employee": "2",
                "employee_name": "Employee 2",
                "leave_type": "Incapacidad",
                "from_date": "2025-07-16",
                "to_date": "2025-07-17",
                "status": "Approved"
            },
            {
                "employee": "2",
                "employee_name": "Employee 2",
                "leave_type": "Permiso personal",
                "from_date": "2025-07-19",
                "to_date": "2025-07-19",
                "status": "Approved"
            },
            # Empleado sin permisos
            {
                "employee": "4",
                "employee_name": "Employee 4",
                "leave_type": "Vacaciones",
                "from_date": "2025-07-20",
                "to_date": "2025-07-20",
                "status": "Approved"
            }
        ]
        
        permisos_dict = procesar_permisos_empleados(leave_data)
        
        # Verificar empleado 1
        assert "1" in permisos_dict
        assert len(permisos_dict["1"]) == 1
        assert date(2025, 7, 16) in permisos_dict["1"]
        
        # Verificar empleado 2 con múltiples permisos
        assert "2" in permisos_dict
        assert len(permisos_dict["2"]) == 3  # 16, 17, 19
        assert date(2025, 7, 16) in permisos_dict["2"]
        assert date(2025, 7, 17) in permisos_dict["2"]
        assert date(2025, 7, 19) in permisos_dict["2"]
        assert permisos_dict["2"][date(2025, 7, 16)]["leave_type"] == "Incapacidad"
        assert permisos_dict["2"][date(2025, 7, 19)]["leave_type"] == "Permiso personal"
        
        # Verificar empleado 4
        assert "4" in permisos_dict
        assert date(2025, 7, 20) in permisos_dict["4"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
