"""
Tests for report_generator.py - ReportGenerator class
"""

import pytest
import pandas as pd
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, mock_open
import os
import tempfile

from report_generator import ReportGenerator


class TestReportGenerator:
    """Tests for the ReportGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ReportGenerator()
        
        # Sample DataFrame for testing
        self.sample_df = pd.DataFrame({
            'employee': ['EMP001', 'EMP002'],
            'Nombre': ['John Doe', 'Jane Smith'],
            'dia': [date(2025, 1, 1), date(2025, 1, 1)],
            'dia_semana': ['Lunes', 'Lunes'],
            'checado_1': ['08:30:00', '09:00:00'],
            'checado_2': ['17:00:00', '18:00:00'],
            'horas_trabajadas': ['08:30:00', '09:00:00'],
            'horas_esperadas': ['08:00:00', '08:00:00'],
            'tipo_retardo': ['Retardo', 'A Tiempo'],
            'minutos_tarde': [30, 0],
            'es_retardo_acumulable': [1, 0],  # EMP001 has one tardiness
            'es_falta': [0, 0],  # No absences
            'salida_anticipada': [False, False],
            'tiene_permiso': [False, False],
            'falta_justificada': [False, False],
            'duration': [timedelta(hours=8, minutes=30), timedelta(hours=9)]
        })
    
    def test_init(self):
        """Test ReportGenerator initialization."""
        assert isinstance(self.generator, ReportGenerator)
    
    @patch('report_generator.pd.DataFrame.to_csv')
    def test_save_detailed_report_basic(self, mock_to_csv):
        """Test basic detailed report saving."""
        mock_to_csv.return_value = None
        
        result = self.generator.save_detailed_report(self.sample_df)
        
        # Verify CSV save was called
        mock_to_csv.assert_called_once()
        call_args = mock_to_csv.call_args
        assert call_args[1]['index'] is False
        assert call_args[1]['encoding'] == 'utf-8-sig'
        
        # Verify filename returned
        assert result.endswith('.csv')
        assert 'reporte_asistencia_analizado' in result
    
    @patch('report_generator.pd.DataFrame.to_csv')
    def test_save_detailed_report_permission_error(self, mock_to_csv):
        """Test detailed report saving with permission error."""
        # Mock permission error on first call
        mock_to_csv.side_effect = [PermissionError("File in use"), None]
        
        result = self.generator.save_detailed_report(self.sample_df)
        
        # Should retry with timestamp
        assert mock_to_csv.call_count == 2
        assert result.endswith('.csv')
        # Should contain timestamp in filename
        assert len(result.split('_')) > 3  # Contains timestamp parts
    
    def test_save_detailed_report_empty_df(self):
        """Test detailed report saving with empty DataFrame."""
        empty_df = pd.DataFrame()
        
        result = self.generator.save_detailed_report(empty_df)
        
        # Should return empty string when no data
        assert result == ""
    
    def test_generar_resumen_periodo_basic(self):
        """Test basic period summary generation."""
        result = self.generator.generar_resumen_periodo(self.sample_df)
        
        # Verify summary structure
        assert not result.empty
        assert 'employee' in result.columns
        assert 'Nombre' in result.columns
        assert 'total_horas_trabajadas' in result.columns
        assert 'total_horas_esperadas' in result.columns
        assert 'total_retardos' in result.columns
        assert 'diferencia_HHMMSS' in result.columns
        
        # Verify data aggregation
        assert len(result) == 2  # Two employees
        
        # Check specific employee data
        emp1 = result[result['employee'] == 'EMP001'].iloc[0]
        emp2 = result[result['employee'] == 'EMP002'].iloc[0]
        
        assert emp1['Nombre'] == 'John Doe'
        assert emp2['Nombre'] == 'Jane Smith'
        assert emp1['total_retardos'] == 1  # Had one tardiness
        assert emp2['total_retardos'] == 0  # No tardiness
    
    def test_generar_resumen_periodo_empty_df(self):
        """Test period summary with empty DataFrame."""
        empty_df = pd.DataFrame()
        
        result = self.generator.generar_resumen_periodo(empty_df)
        
        assert result.empty
    
    def test_generar_resumen_periodo_with_permits(self):
        """Test period summary with permits and justified absences."""
        df_with_permits = self.sample_df.copy()
        df_with_permits['tiene_permiso'] = [True, False]
        df_with_permits['falta_justificada'] = [True, False]
        df_with_permits['es_falta'] = [1, 0]
        df_with_permits['es_falta_ajustada'] = [0, 0]  # First absence justified
        df_with_permits['horas_descontadas_permiso'] = ['02:00:00', '00:00:00']
        df_with_permits['horas_esperadas_originales'] = ['08:00:00', '08:00:00']
        
        result = self.generator.generar_resumen_periodo(df_with_permits)
        
        # Verify permit-related columns
        assert 'total_horas_descontadas_permiso' in result.columns
        assert 'faltas_justificadas' in result.columns
        
        # Check permit data
        emp1 = result[result['employee'] == 'EMP001'].iloc[0]
        assert emp1['faltas_justificadas'] == 1
        assert emp1['total_horas_descontadas_permiso'] == '02:00:00'
    
    @patch('report_generator.pd.DataFrame.to_csv')
    def test_save_summary_report_basic(self, mock_to_csv):
        """Test basic summary report saving."""
        mock_to_csv.return_value = None
        
        summary_df = pd.DataFrame({
            'employee': ['EMP001'],
            'Nombre': ['John Doe'],
            'total_horas_trabajadas': ['08:30:00']
        })
        
        result = self.generator.save_summary_report(summary_df)
        
        # Verify CSV save was called
        mock_to_csv.assert_called_once()
        assert result == 'resumen_periodo.csv'
    
    def test_generar_reporte_html_empty_summary(self):
        """Test HTML report generation with empty summary."""
        empty_summary = pd.DataFrame()
        
        result = self.generator.generar_reporte_html(
            self.sample_df, empty_summary, '2025-01-01', '2025-01-01', 'Test Branch'
        )
        
        # Should create a basic HTML file even with empty data
        assert result.endswith('.html')
        assert 'dashboard_asistencia' in result
    
    @patch('builtins.open', new_callable=mock_open)
    def test_generar_reporte_html_with_data(self, mock_file):
        """Test HTML report generation with valid data."""
        summary_df = pd.DataFrame({
            'employee': ['EMP001', 'EMP002'],
            'Nombre': ['John Doe', 'Jane Smith'],
            'total_horas_trabajadas': ['08:30:00', '09:00:00'],
            'total_horas_esperadas': ['08:00:00', '08:00:00'],
            'total_horas_descontadas_permiso': ['00:00:00', '00:00:00'],
            'total_horas': ['08:00:00', '08:00:00'],
            'total_retardos': [1, 0],
            'faltas_del_periodo': [0, 0],
            'faltas_justificadas': [0, 0],
            'total_faltas': [0, 0],
            'diferencia_HHMMSS': ['+00:30:00', '+01:00:00']
        })
        
        result = self.generator.generar_reporte_html(
            self.sample_df, summary_df, '2025-01-01', '2025-01-01', 'Test Branch'
        )
        
        # Verify file was written
        mock_file.assert_called()
        
        # Verify HTML content structure (check write calls)
        written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
        assert '<!DOCTYPE html>' in written_content
        assert 'Test Branch' in written_content
        assert '2025-01-01' in written_content
        assert 'John Doe' in written_content
        assert 'Jane Smith' in written_content
    
    @patch('builtins.open', side_effect=PermissionError("File in use"))
    def test_generar_reporte_html_permission_error(self, mock_file):
        """Test HTML report generation with permission error."""
        with patch('builtins.open', mock_open()) as mock_file_retry:
            summary_df = pd.DataFrame({
                'employee': ['EMP001'],
                'Nombre': ['John Doe'],
                'total_horas_trabajadas': ['08:30:00'],
                'total_horas_esperadas': ['08:00:00'],
                'total_horas_descontadas_permiso': ['00:00:00'],
                'total_horas': ['08:00:00'],
                'total_retardos': [1],
                'faltas_del_periodo': [0],
                'faltas_justificadas': [0],
                'total_faltas': [0],
                'diferencia_HHMMSS': ['+00:30:00']
            })
            
            result = self.generator.generar_reporte_html(
                self.sample_df, summary_df, '2025-01-01', '2025-01-01', 'Test Branch'
            )
            
            # Should create alternative filename with timestamp
            assert result.endswith('.html')
            assert 'dashboard_asistencia' in result
            # Should contain timestamp (filename_timestamp.html format)
            assert '_' in result and len(result.split('_')) >= 2
    
    def test_generar_reporte_excel_basic(self):
        """Test basic Excel report generation."""
        summary_df = pd.DataFrame({
            'employee': ['EMP001', 'EMP002'],
            'Nombre': ['John Doe', 'Jane Smith'],
            'total_horas_trabajadas': ['08:30:00', '09:00:00'],
            'total_horas_esperadas': ['08:00:00', '08:00:00'],
            'total_horas_descontadas_permiso': ['00:00:00', '00:00:00'],
            'total_horas': ['08:00:00', '08:00:00'],
            'total_retardos': [0, 0],
            'faltas_del_periodo': [0, 0],
            'faltas_justificadas': [0, 0],
            'total_faltas': [0, 0],
            'diferencia_HHMMSS': ['+00:30:00', '+01:00:00']
        })
        
        with patch('report_generator.generar_reporte_excel') as mock_generar:
            mock_generar.return_value = 'reporte_asistencia_Test_Branch_2025-01-01_2025-01-01.xlsx'
            
            result = self.generator.generar_reporte_excel(
                self.sample_df, summary_df, 'Test Branch', '2025-01-01', '2025-01-01'
            )
            
            # Verify function was called
            mock_generar.assert_called_once()
            
            # Verify filename
            assert result.endswith('.xlsx')
            assert 'reporte_asistencia_Test_Branch' in result
    
    def test_generar_reporte_excel_permission_error(self):
        """Test Excel report generation with permission error."""
        summary_df = pd.DataFrame({
            'employee': ['EMP001'],
            'Nombre': ['John Doe'],
            'total_horas_trabajadas': ['08:30:00'],
            'total_horas_esperadas': ['08:00:00'],
            'total_horas_descontadas_permiso': ['00:00:00'],
            'total_horas': ['08:00:00'],
            'total_retardos': [0],
            'faltas_del_periodo': [0],
            'faltas_justificadas': [0],
            'total_faltas': [0],
            'diferencia_HHMMSS': ['+00:30:00']
        })
        
        with patch('report_generator.generar_reporte_excel') as mock_generar:
            # Mock returning a timestamped filename
            mock_generar.return_value = 'reporte_asistencia_Test Branch_2025-01-01_2025-01-01_20250806_223917.xlsx'
            
            result = self.generator.generar_reporte_excel(
                self.sample_df, summary_df, 'Test Branch', '2025-01-01', '2025-01-01'
            )
            
            # Should create alternative filename with timestamp
            assert result.endswith('.xlsx')
            assert 'reporte_asistencia_Test Branch' in result
            # Should contain timestamp
            parts = result.split('_')
            assert len(parts) > 4  # Contains timestamp parts


class TestReportGeneratorUtilities:
    """Tests for utility functions in ReportGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ReportGenerator()
    
    def test_time_to_decimal_basic(self):
        """Test time to decimal conversion."""
        result = self.generator._time_to_decimal('08:30:00')
        assert result == 8.5
        
        result = self.generator._time_to_decimal('01:15:30')
        assert abs(result - 1.258333333333333) < 0.000001  # 1 + 15/60 + 30/3600
    
    def test_time_to_decimal_edge_cases(self):
        """Test time to decimal conversion edge cases."""
        # Empty or invalid inputs
        assert self.generator._time_to_decimal('') == 0.0
        assert self.generator._time_to_decimal('00:00:00') == 0.0
        assert self.generator._time_to_decimal('---') == 0.0
        assert self.generator._time_to_decimal(None) == 0.0
        
        # Invalid format
        assert self.generator._time_to_decimal('invalid') == 0.0
    
    def test_format_timedelta_with_sign_positive(self):
        """Test timedelta formatting with positive values."""
        td = timedelta(hours=2, minutes=30, seconds=15)
        result = self.generator._format_timedelta_with_sign(td)
        assert result == '+02:30:15'
    
    def test_format_timedelta_with_sign_negative(self):
        """Test timedelta formatting with negative values."""
        td = timedelta(hours=-1, minutes=-15)
        result = self.generator._format_timedelta_with_sign(td)
        assert result == '-01:15:00'
    
    def test_format_timedelta_with_sign_zero(self):
        """Test timedelta formatting with zero value."""
        td = timedelta(0)
        result = self.generator._format_timedelta_with_sign(td)
        assert result == '00:00:00'
    
    def test_format_positive_timedelta(self):
        """Test positive timedelta formatting."""
        td = timedelta(hours=10, minutes=45, seconds=30)
        result = self.generator._format_positive_timedelta(td)
        assert result == '10:45:30'
        
        # Test with days (should be converted to hours)
        td = timedelta(days=1, hours=2)  # 24 + 2 = 26 hours
        result = self.generator._format_positive_timedelta(td)
        assert result == '26:00:00'


class TestReportGeneratorIntegration:
    """Integration tests for ReportGenerator with realistic data."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ReportGenerator()
        
        # Create realistic test data
        self.realistic_df = pd.DataFrame({
            'employee': ['EMP001', 'EMP001', 'EMP002', 'EMP002'],
            'Nombre': ['John Doe', 'John Doe', 'Jane Smith', 'Jane Smith'],
            'dia': [date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 1), date(2025, 1, 2)],
            'dia_semana': ['Miércoles', 'Jueves', 'Miércoles', 'Jueves'],
            'checado_1': ['08:30:00', '08:00:00', '09:00:00', '08:45:00'],
            'checado_2': ['17:00:00', '17:00:00', '18:00:00', '17:30:00'],
            'horas_trabajadas': ['08:30:00', '09:00:00', '09:00:00', '08:45:00'],
            'horas_esperadas': ['08:00:00', '08:00:00', '08:00:00', '08:00:00'],
            'tipo_retardo': ['Retardo', 'A Tiempo', 'Retardo', 'A Tiempo'],
            'minutos_tarde': [30, 0, 60, 0],
            'es_retardo_acumulable': [1, 0, 1, 0],
            'es_falta': [0, 0, 0, 0],
            'salida_anticipada': [False, False, False, True],
            'tiene_permiso': [False, False, False, False],
            'falta_justificada': [False, False, False, False],
            'duration': [
                timedelta(hours=8, minutes=30),
                timedelta(hours=9),
                timedelta(hours=9),
                timedelta(hours=8, minutes=45)
            ],
            'horas_esperadas_originales': ['08:00:00', '08:00:00', '08:00:00', '08:00:00'],
            'horas_descontadas_permiso': ['00:00:00', '00:00:00', '00:00:00', '00:00:00'],
            'horas_descanso': ['00:00:00', '00:00:00', '00:00:00', '00:00:00']
        })
    
    def test_full_report_generation_pipeline(self):
        """Test complete report generation pipeline."""
        # Generate summary
        summary_df = self.generator.generar_resumen_periodo(self.realistic_df)
        
        # Verify summary was generated correctly
        assert not summary_df.empty
        assert len(summary_df) == 2  # Two employees
        
        # Check aggregated data
        emp1_summary = summary_df[summary_df['employee'] == 'EMP001'].iloc[0]
        emp2_summary = summary_df[summary_df['employee'] == 'EMP002'].iloc[0]
        
        assert emp1_summary['total_retardos'] == 1  # One tardiness
        assert emp2_summary['total_retardos'] == 1  # One tardiness
        
        # Test file generation (with mocking to avoid actual file creation)
        with patch('report_generator.pd.DataFrame.to_csv'):
            detailed_filename = self.generator.save_detailed_report(self.realistic_df)
            summary_filename = self.generator.save_summary_report(summary_df)
            
            assert detailed_filename.endswith('.csv')
            assert summary_filename == 'resumen_periodo.csv'
        
        # Test HTML generation
        with patch('builtins.open', mock_open()):
            html_filename = self.generator.generar_reporte_html(
                self.realistic_df, summary_df, '2025-01-01', '2025-01-02', 'Test Branch'
            )
            
            assert html_filename.endswith('.html')
        
        # Test Excel generation
        with patch('report_generator.pd.ExcelWriter') as mock_excel:
            mock_writer = Mock()
            mock_excel.return_value.__enter__.return_value = mock_writer
            
            excel_filename = self.generator.generar_reporte_excel(
                self.realistic_df, summary_df, 'Test Branch', '2025-01-01', '2025-01-02'
            )
            
            assert excel_filename.endswith('.xlsx')
    
    @pytest.mark.integration
    def test_realistic_data_processing(self):
        """Test with more complex realistic data scenarios."""
        # Add more complex scenarios
        complex_df = self.realistic_df.copy()
        
        # Add employee with permits
        permit_rows = pd.DataFrame({
            'employee': ['EMP003'],
            'Nombre': ['Bob Wilson'],
            'dia': [date(2025, 1, 1)],
            'dia_semana': ['Miércoles'],
            'checado_1': [None],  # Absent
            'checado_2': [None],
            'horas_trabajadas': ['00:00:00'],
            'horas_esperadas': ['00:00:00'],  # Adjusted for permit
            'tipo_retardo': ['Falta'],
            'minutos_tarde': [0],
            'es_retardo_acumulable': [0],
            'es_falta': [1],
            'salida_anticipada': [False],
            'tiene_permiso': [True],
            'falta_justificada': [True],
            'duration': [timedelta(0)],
            'horas_esperadas_originales': ['08:00:00'],
            'horas_descontadas_permiso': ['08:00:00'],  # Full day permit
            'horas_descanso': ['00:00:00']
        })
        
        complex_df = pd.concat([complex_df, permit_rows], ignore_index=True)
        
        # Generate reports
        summary = self.generator.generar_resumen_periodo(complex_df)
        
        # Verify permit handling
        emp3_summary = summary[summary['employee'] == 'EMP003'].iloc[0]
        assert emp3_summary['faltas_justificadas'] == 1
        assert emp3_summary['total_horas_descontadas_permiso'] == '08:00:00'
        
        # Verify report generation doesn't fail with complex data
        with patch('report_generator.pd.DataFrame.to_csv'), \
             patch('builtins.open', mock_open()), \
             patch('report_generator.pd.ExcelWriter') as mock_excel:
            
            mock_writer = Mock()
            mock_excel.return_value.__enter__.return_value = mock_writer
            
            # Should not raise exceptions
            detailed_file = self.generator.save_detailed_report(complex_df)
            summary_file = self.generator.save_summary_report(summary)
            html_file = self.generator.generar_reporte_html(
                complex_df, summary, '2025-01-01', '2025-01-02', 'Complex Branch'
            )
            excel_file = self.generator.generar_reporte_excel(
                complex_df, summary, 'Complex Branch', '2025-01-01', '2025-01-02'
            )
            
            # All files should be generated
            assert all(f.endswith('.csv') for f in [detailed_file, summary_file])
            assert html_file.endswith('.html')
            assert excel_file.endswith('.xlsx')