"""
Tests for data_processor.py - AttendanceProcessor class
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta, date, time
from unittest.mock import Mock, patch, MagicMock

from data_processor import AttendanceProcessor


class TestAttendanceProcessor:
    """Tests for the AttendanceProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = AttendanceProcessor()
    
    def test_init(self):
        """Test AttendanceProcessor initialization."""
        assert isinstance(self.processor, AttendanceProcessor)
    
    def test_process_checkins_to_dataframe_empty(self):
        """Test processing empty checkin data."""
        result = self.processor.process_checkins_to_dataframe([], '2025-01-01', '2025-01-01')
        assert result.empty
    
    def test_process_checkins_to_dataframe_basic(self):
        """Test basic checkin data processing."""
        checkin_data = [
            {
                'employee': 'EMP001',
                'employee_name': 'John Doe',
                'time': '2025-01-01T08:30:00'
            },
            {
                'employee': 'EMP001',
                'employee_name': 'John Doe',
                'time': '2025-01-01T17:00:00'
            }
        ]
        
        result = self.processor.process_checkins_to_dataframe(
            checkin_data, '2025-01-01', '2025-01-01'
        )
        
        # Verify basic structure
        assert not result.empty
        assert 'employee' in result.columns
        assert 'Nombre' in result.columns
        assert 'dia' in result.columns
        assert 'checado_1' in result.columns
        assert 'checado_2' in result.columns
        assert 'horas_trabajadas' in result.columns
        assert 'duration' in result.columns
        
        # Verify data content
        emp_row = result[result['employee'] == 'EMP001'].iloc[0]
        assert emp_row['Nombre'] == 'John Doe'
        assert emp_row['checado_1'] == '08:30:00'
        assert emp_row['checado_2'] == '17:00:00'
        assert emp_row['dia'] == date(2025, 1, 1)
    
    def test_process_checkins_to_dataframe_multiple_employees(self):
        """Test processing checkins for multiple employees."""
        checkin_data = [
            {'employee': 'EMP001', 'employee_name': 'John Doe', 'time': '2025-01-01T08:30:00'},
            {'employee': 'EMP001', 'employee_name': 'John Doe', 'time': '2025-01-01T17:00:00'},
            {'employee': 'EMP002', 'employee_name': 'Jane Smith', 'time': '2025-01-01T09:00:00'},
            {'employee': 'EMP002', 'employee_name': 'Jane Smith', 'time': '2025-01-01T18:00:00'},
        ]
        
        result = self.processor.process_checkins_to_dataframe(
            checkin_data, '2025-01-01', '2025-01-01'
        )
        
        # Verify both employees are included
        employees = result['employee'].unique()
        assert 'EMP001' in employees
        assert 'EMP002' in employees
        
        # Verify each employee has correct data
        emp1_row = result[result['employee'] == 'EMP001'].iloc[0]
        emp2_row = result[result['employee'] == 'EMP002'].iloc[0]
        
        assert emp1_row['Nombre'] == 'John Doe'
        assert emp2_row['Nombre'] == 'Jane Smith'
        assert emp1_row['checado_1'] == '08:30:00'
        assert emp2_row['checado_1'] == '09:00:00'
    
    def test_process_checkins_to_dataframe_multiple_days(self):
        """Test processing checkins across multiple days."""
        checkin_data = [
            {'employee': 'EMP001', 'employee_name': 'John Doe', 'time': '2025-01-01T08:30:00'},
            {'employee': 'EMP001', 'employee_name': 'John Doe', 'time': '2025-01-01T17:00:00'},
            {'employee': 'EMP001', 'employee_name': 'John Doe', 'time': '2025-01-02T08:45:00'},
            {'employee': 'EMP001', 'employee_name': 'John Doe', 'time': '2025-01-02T17:15:00'},
        ]
        
        result = self.processor.process_checkins_to_dataframe(
            checkin_data, '2025-01-01', '2025-01-02'
        )
        
        # Verify both days are included
        dates = result['dia'].unique()
        assert date(2025, 1, 1) in dates
        assert date(2025, 1, 2) in dates
        
        # Verify data for each day
        day1_row = result[result['dia'] == date(2025, 1, 1)].iloc[0]
        day2_row = result[result['dia'] == date(2025, 1, 2)].iloc[0]
        
        assert day1_row['checado_1'] == '08:30:00'
        assert day1_row['checado_2'] == '17:00:00'
        assert day2_row['checado_1'] == '08:45:00'
        assert day2_row['checado_2'] == '17:15:00'
    
    def test_process_checkins_to_dataframe_multiple_checkins(self):
        """Test processing multiple checkins per day (breaks)."""
        checkin_data = [
            {'employee': 'EMP001', 'employee_name': 'John Doe', 'time': '2025-01-01T08:00:00'},
            {'employee': 'EMP001', 'employee_name': 'John Doe', 'time': '2025-01-01T12:00:00'},
            {'employee': 'EMP001', 'employee_name': 'John Doe', 'time': '2025-01-01T13:00:00'},
            {'employee': 'EMP001', 'employee_name': 'John Doe', 'time': '2025-01-01T17:00:00'},
        ]
        
        result = self.processor.process_checkins_to_dataframe(
            checkin_data, '2025-01-01', '2025-01-01'
        )
        
        # Verify all checkins are captured
        emp_row = result[result['employee'] == 'EMP001'].iloc[0]
        assert emp_row['checado_1'] == '08:00:00'
        assert emp_row['checado_2'] == '12:00:00'
        assert emp_row['checado_3'] == '13:00:00'
        assert emp_row['checado_4'] == '17:00:00'
    
    def test_calcular_horas_descanso_insufficient_checkins(self):
        """Test break calculation with insufficient checkins."""
        # Create a mock row with less than 4 checkins
        test_row = pd.Series({
            'checado_1': '08:00:00',
            'checado_2': '17:00:00',
            'checado_3': None
        })
        
        result = self.processor.calcular_horas_descanso(test_row)
        assert result == timedelta(0)
    
    def test_calcular_horas_descanso_valid_break(self):
        """Test break calculation with valid break period."""
        test_row = pd.Series({
            'checado_1': '08:00:00',  # Entry
            'checado_2': '12:00:00',  # Break start
            'checado_3': '13:00:00',  # Break end
            'checado_4': '17:00:00',  # Exit
        })
        
        result = self.processor.calcular_horas_descanso(test_row)
        assert result == timedelta(hours=1)  # 1 hour break
    
    def test_calcular_horas_descanso_multiple_breaks(self):
        """Test break calculation with multiple break periods."""
        test_row = pd.Series({
            'checado_1': '08:00:00',  # Entry
            'checado_2': '10:00:00',  # Break 1 start
            'checado_3': '10:30:00',  # Break 1 end
            'checado_4': '12:00:00',  # Break 2 start
            'checado_5': '13:00:00',  # Break 2 end
            'checado_6': '17:00:00',  # Exit
        })
        
        result = self.processor.calcular_horas_descanso(test_row)
        # Should be 0.5 hours (10:30-10:00) + 1 hour (13:00-12:00) = 1.5 hours
        assert result == timedelta(hours=1, minutes=30)
    
    @patch('data_processor.obtener_horario_empleado')
    def test_procesar_horarios_con_medianoche_no_midnight_crossing(self, mock_obtener_horario):
        """Test midnight processing for normal shifts."""
        # Mock schedule without midnight crossing
        mock_obtener_horario.return_value = {
            'hora_entrada': '08:00',
            'hora_salida': '17:00',
            'cruza_medianoche': False,
            'horas_totales': 8.0
        }
        
        # Create test DataFrame
        df = pd.DataFrame({
            'employee': ['EMP001'],
            'dia': [date(2025, 1, 1)],
            'dia_iso': [2],  # Tuesday
            'es_primera_quincena': [True],
            'checado_1': ['08:30:00'],
            'checado_2': ['17:00:00']
        })
        
        cache_horarios = {'EMP001': {True: {2: mock_obtener_horario.return_value}}}
        
        result = self.processor.procesar_horarios_con_medianoche(df, cache_horarios)
        
        # For non-midnight shifts, should return unchanged
        assert len(result) == 1
        assert result.iloc[0]['checado_1'] == '08:30:00'
        assert result.iloc[0]['checado_2'] == '17:00:00'
    
    @patch('data_processor.obtener_horario_empleado')
    def test_procesar_horarios_con_medianoche_with_midnight_crossing(self, mock_obtener_horario):
        """Test midnight processing for night shifts."""
        # Mock night shift schedule
        mock_obtener_horario.return_value = {
            'hora_entrada': '22:00',
            'hora_salida': '06:00',
            'cruza_medianoche': True,
            'horas_totales': 8.0
        }
        
        # Create test DataFrame with night shift marks
        df = pd.DataFrame({
            'employee': ['EMP001', 'EMP001'],
            'dia': [date(2025, 1, 1), date(2025, 1, 2)],
            'dia_iso': [2, 3],  # Tuesday, Wednesday
            'es_primera_quincena': [True, True],
            'checado_1': ['22:30:00', None],  # Entry on Tuesday
            'checado_2': [None, '06:30:00']   # Exit on Wednesday
        })
        
        cache_horarios = {'EMP001': {True: {2: mock_obtener_horario.return_value}}}
        
        result = self.processor.procesar_horarios_con_medianoche(df, cache_horarios)
        
        # Should process night shift correctly
        # The exact logic depends on the complex midnight crossing implementation
        assert not result.empty
        # Additional assertions would depend on the specific night shift logic
    
    def test_aplicar_calculo_horas_descanso_empty_df(self):
        """Test break calculation application on empty DataFrame."""
        df = pd.DataFrame()
        result = self.processor.aplicar_calculo_horas_descanso(df)
        assert result.empty
    
    def test_aplicar_calculo_horas_descanso_with_breaks(self):
        """Test break calculation application with valid breaks."""
        df = pd.DataFrame({
            'employee': ['EMP001'],
            'dia': [date(2025, 1, 1)],
            'checado_1': ['08:00:00'],
            'checado_2': ['12:00:00'],
            'checado_3': ['13:00:00'],
            'checado_4': ['17:00:00'],
            'horas_trabajadas': ['09:00:00'],
            'horas_esperadas': ['08:00:00'],
            'duration': [timedelta(hours=9)]
        })
        
        result = self.processor.aplicar_calculo_horas_descanso(df)
        
        # Verify break hours were calculated
        assert 'horas_descanso' in result.columns
        assert 'horas_descanso_td' in result.columns
        assert result.iloc[0]['horas_descanso'] == '01:00:00'  # 1 hour break
        
        # Verify original values are preserved (no longer adjusting worked hours)
        assert result.iloc[0]['horas_trabajadas'] == '09:00:00'  # Original hours preserved
        assert result.iloc[0]['horas_esperadas'] == '08:00:00'  # Original hours preserved
        
        # Verify original values are saved for reference
        assert 'horas_trabajadas_originales' in result.columns
        assert 'horas_esperadas_originales' in result.columns
    
    @patch('data_processor.obtener_horario_empleado')
    def test_analizar_asistencia_con_horarios_cache_basic(self, mock_obtener_horario):
        """Test basic attendance analysis."""
        # Mock schedule
        mock_obtener_horario.return_value = {
            'hora_entrada': '08:00',
            'hora_salida': '17:00',
            'cruza_medianoche': False,
            'horas_totales': 8.0
        }
        
        df = pd.DataFrame({
            'employee': ['EMP001'],
            'dia': [date(2025, 1, 1)],
            'dia_iso': [2],
            'es_primera_quincena': [True],
            'checado_1': ['08:30:00'],  # 30 minutes late
            'checado_2': ['17:00:00']
        })
        
        cache_horarios = {'EMP001': {True: {2: mock_obtener_horario.return_value}}}
        
        result = self.processor.analizar_asistencia_con_horarios_cache(df, cache_horarios)
        
        # Verify analysis columns are added
        assert 'hora_entrada_programada' in result.columns
        assert 'hora_salida_programada' in result.columns
        assert 'tipo_retardo' in result.columns
        assert 'minutos_tarde' in result.columns
        assert 'salida_anticipada' in result.columns
        
        # Verify analysis results
        assert result.iloc[0]['hora_entrada_programada'] == '08:00'
        assert result.iloc[0]['tipo_retardo'] == 'Retardo'  # 30 minutes late
        assert result.iloc[0]['minutos_tarde'] == 30
    
    def test_ajustar_horas_esperadas_con_permisos_no_permits(self):
        """Test hours adjustment without permits."""
        df = pd.DataFrame({
            'employee': ['EMP001'],
            'dia': [date(2025, 1, 1)],
            'horas_esperadas': ['08:00:00']
        })
        
        permisos_dict = {}  # No permits
        cache_horarios = {}
        
        result = self.processor.ajustar_horas_esperadas_con_permisos(
            df, permisos_dict, cache_horarios
        )
        
        # Verify permit columns are added
        assert 'tiene_permiso' in result.columns
        assert 'tipo_permiso' in result.columns
        assert 'es_permiso_medio_dia' in result.columns
        
        # Verify no permits
        assert result.iloc[0]['tiene_permiso'] == False
        assert pd.isna(result.iloc[0]['tipo_permiso'])
    
    def test_ajustar_horas_esperadas_con_permisos_full_day(self):
        """Test hours adjustment with full day permit."""
        df = pd.DataFrame({
            'employee': ['EMP001'],
            'dia': [date(2025, 1, 1)],
            'horas_esperadas': ['08:00:00']
        })
        
        permisos_dict = {
            'EMP001': {
                date(2025, 1, 1): {
                    'leave_type': 'Vacations',
                    'leave_type_normalized': 'vacations',
                    'is_half_day': False
                }
            }
        }
        cache_horarios = {}
        
        result = self.processor.ajustar_horas_esperadas_con_permisos(
            df, permisos_dict, cache_horarios
        )
        
        # Verify permit was applied
        assert result.iloc[0]['tiene_permiso'] == True
        assert result.iloc[0]['tipo_permiso'] == 'Vacations'
        assert result.iloc[0]['es_permiso_medio_dia'] == False
        assert result.iloc[0]['horas_esperadas'] == '00:00:00'  # Full day leave
    
    def test_ajustar_horas_esperadas_con_permisos_half_day(self):
        """Test hours adjustment with half day permit."""
        df = pd.DataFrame({
            'employee': ['EMP001'],
            'dia': [date(2025, 1, 1)],
            'horas_esperadas': ['08:00:00']
        })
        
        permisos_dict = {
            'EMP001': {
                date(2025, 1, 1): {
                    'leave_type': 'Personal Leave',
                    'leave_type_normalized': 'personal',
                    'is_half_day': True
                }
            }
        }
        cache_horarios = {}
        
        result = self.processor.ajustar_horas_esperadas_con_permisos(
            df, permisos_dict, cache_horarios
        )
        
        # Verify half day permit was applied
        assert result.iloc[0]['tiene_permiso'] == True
        assert result.iloc[0]['es_permiso_medio_dia'] == True
        assert result.iloc[0]['horas_esperadas'] == '04:00:00'  # Half of 8 hours
    
    def test_aplicar_regla_perdon_retardos_basic(self):
        """Test basic tardiness forgiveness rule."""
        df = pd.DataFrame({
            'employee': ['EMP001'],
            'tipo_retardo': ['Retardo'],
            'minutos_tarde': [30],
            'horas_trabajadas': ['08:30:00'],  # Worked extra 30 minutes
            'horas_esperadas': ['08:00:00']
        })
        
        result = self.processor.aplicar_regla_perdon_retardos(df)
        
        # Verify forgiveness columns are added
        assert 'retardo_perdonado' in result.columns
        assert 'tipo_retardo_original' in result.columns
        assert 'minutos_tarde_original' in result.columns
        assert 'cumplio_horas_turno' in result.columns
        
        # Verify tardiness was forgiven (worked more than expected)
        assert result.iloc[0]['retardo_perdonado'] == True
        assert result.iloc[0]['tipo_retardo'] == 'A Tiempo (Cumplió Horas)'
        assert result.iloc[0]['tipo_retardo_original'] == 'Retardo'
        assert result.iloc[0]['minutos_tarde'] == 0  # Forgiven
        assert result.iloc[0]['minutos_tarde_original'] == 30
    
    def test_aplicar_regla_perdon_retardos_no_forgiveness(self):
        """Test tardiness forgiveness when hours not met."""
        df = pd.DataFrame({
            'employee': ['EMP001'],
            'tipo_retardo': ['Retardo'],
            'minutos_tarde': [30],
            'horas_trabajadas': ['07:30:00'],  # Worked less than expected
            'horas_esperadas': ['08:00:00']
        })
        
        result = self.processor.aplicar_regla_perdon_retardos(df)
        
        # Verify no forgiveness
        assert result.iloc[0]['retardo_perdonado'] == False
        assert result.iloc[0]['tipo_retardo'] == 'Retardo'  # Unchanged
        assert result.iloc[0]['minutos_tarde'] == 30  # Unchanged
    
    def test_clasificar_faltas_con_permisos_basic(self):
        """Test absence classification with permits."""
        df = pd.DataFrame({
            'employee': ['EMP001'],
            'tipo_retardo': ['Falta'],
            'tiene_permiso': [True]
        })
        
        result = self.processor.clasificar_faltas_con_permisos(df)
        
        # Verify classification columns are added
        assert 'tipo_falta_ajustada' in result.columns
        assert 'falta_justificada' in result.columns
        assert 'es_falta_ajustada' in result.columns
        
        # Verify absence was justified
        assert result.iloc[0]['tipo_falta_ajustada'] == 'Falta Justificada'
        assert result.iloc[0]['falta_justificada'] == True
        assert result.iloc[0]['es_falta_ajustada'] == 0  # Not an unjustified absence
    
    def test_clasificar_faltas_con_permisos_no_permit(self):
        """Test absence classification without permits."""
        df = pd.DataFrame({
            'employee': ['EMP001'],
            'tipo_retardo': ['Falta'],
            'tiene_permiso': [False]
        })
        
        result = self.processor.clasificar_faltas_con_permisos(df)
        
        # Verify absence remains unjustified
        assert result.iloc[0]['tipo_falta_ajustada'] == 'Falta'
        assert result.iloc[0]['falta_justificada'] == False
        assert result.iloc[0]['es_falta_ajustada'] == 1  # Still an unjustified absence

    def test_marcar_dias_no_contratado(self):
        """Test that days before joining date are marked as 'No Contratado' permit."""
        df = pd.DataFrame({
            'employee': ['EMP001', 'EMP001', 'EMP001'],
            'dia': [date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3)],
            'horas_esperadas': ['08:00:00', '08:00:00', '08:00:00'],
            'tipo_retardo': ['Falta', 'A Tiempo', 'Falta'],
            'es_falta': [1, 0, 1],
            'tiene_permiso': [False, False, False],
            'tipo_permiso': [None, None, None]
        })
        joining_dates = {'EMP001': date(2025, 1, 2)}

        result = self.processor.marcar_dias_no_contratado(df, joining_dates)

        # Day before joining date
        day1 = result[result['dia'] == date(2025, 1, 1)].iloc[0]
        assert day1['tiene_permiso'] == True
        assert day1['tipo_permiso'] == 'No Contratado'
        assert day1['horas_esperadas'] == '00:00:00'
        assert day1['tipo_retardo'] == 'No Contratado'
        assert day1['es_falta'] == 0

        # Day of joining (should be unchanged)
        day2 = result[result['dia'] == date(2025, 1, 2)].iloc[0]
        assert day2['tiene_permiso'] == False
        assert pd.isna(day2['tipo_permiso'])
        assert day2['tipo_retardo'] == 'A Tiempo'

        # Day after joining (should be unchanged)
        day3 = result[result['dia'] == date(2025, 1, 3)].iloc[0]
        assert day3['tiene_permiso'] == False
        assert pd.isna(day3['tipo_permiso'])
        assert day3['tipo_retardo'] == 'Falta'


class TestAttendanceProcessorIntegration:
    """Integration tests for AttendanceProcessor methods working together."""
    
    def test_full_processing_pipeline(self):
        """Test the complete processing pipeline."""
        processor = AttendanceProcessor()
        
        # Sample checkin data
        checkin_data = [
            {'employee': 'EMP001', 'employee_name': 'John Doe', 'time': '2025-01-01T08:30:00'},
            {'employee': 'EMP001', 'employee_name': 'John Doe', 'time': '2025-01-01T12:00:00'},
            {'employee': 'EMP001', 'employee_name': 'John Doe', 'time': '2025-01-01T13:00:00'},
            {'employee': 'EMP001', 'employee_name': 'John Doe', 'time': '2025-01-01T17:00:00'},
        ]
        
        # Mock cache and permits
        cache_horarios = {
            'EMP001': {
                True: {
                    2: {  # Tuesday
                        'hora_entrada': '08:00',
                        'hora_salida': '17:00',
                        'cruza_medianoche': False,
                        'horas_totales': 8.0
                    }
                }
            }
        }
        
        permisos_dict = {}  # No permits
        
        # Execute pipeline
        df = processor.process_checkins_to_dataframe(checkin_data, '2025-01-01', '2025-01-01')
        df = processor.procesar_horarios_con_medianoche(df, cache_horarios)
        df = processor.analizar_asistencia_con_horarios_cache(df, cache_horarios)
        df = processor.aplicar_calculo_horas_descanso(df)
        df = processor.ajustar_horas_esperadas_con_permisos(df, permisos_dict, cache_horarios)
        df = processor.aplicar_regla_perdon_retardos(df)
        df = processor.clasificar_faltas_con_permisos(df)
        
        # Verify final result
        assert not df.empty
        assert len(df) == 1
        
        result_row = df.iloc[0]
        
        # Verify all processing steps completed
        assert 'checado_1' in df.columns
        assert 'tipo_retardo' in df.columns
        assert 'horas_descanso' in df.columns
        assert 'tiene_permiso' in df.columns
        assert 'retardo_perdonado' in df.columns
        assert 'tipo_falta_ajustada' in df.columns
        
        # Verify basic data integrity
        assert result_row['employee'] == 'EMP001'
        assert result_row['Nombre'] == 'John Doe'
        assert result_row['dia'] == date(2025, 1, 1)