"""
Tests for main.py - AttendanceReportManager orchestration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pandas as pd

from main import AttendanceReportManager, main
from config import validate_api_credentials


class TestAttendanceReportManager:
    """Tests for the main orchestration class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = AttendanceReportManager()
    
    def test_init(self):
        """Test initialization of AttendanceReportManager."""
        assert hasattr(self.manager, 'api_client')
        assert hasattr(self.manager, 'processor')
        assert hasattr(self.manager, 'report_generator')
        
        # Verify correct types
        from api_client import APIClient
        from data_processor import AttendanceProcessor
        from report_generator import ReportGenerator
        
        assert isinstance(self.manager.api_client, APIClient)
        assert isinstance(self.manager.processor, AttendanceProcessor)
        assert isinstance(self.manager.report_generator, ReportGenerator)
    
    @patch('main.validate_api_credentials')
    @patch('main.connect_db')
    @patch('main.obtener_codigos_empleados_api')
    @patch('main.procesar_permisos_empleados')
    @patch('main.obtener_horarios_multi_quincena')
    @patch('main.mapear_horarios_por_empleado_multi')
    @patch('main.determine_period_type')
    def test_generate_attendance_report_success(
        self, mock_determine_period, mock_mapear_horarios, mock_obtener_horarios,
        mock_procesar_permisos, mock_obtener_codigos, mock_connect_db, mock_validate_api
    ):
        """Test successful attendance report generation."""
        
        # Mock setup
        mock_validate_api.return_value = None
        mock_connect_db.return_value = MagicMock()
        mock_obtener_codigos.return_value = ['EMP001', 'EMP002']
        mock_procesar_permisos.return_value = {}
        mock_determine_period.return_value = (True, False)
        mock_obtener_horarios.return_value = {'primera': [{'employee': 'EMP001', 'hora_entrada': '08:00', 'hora_salida': '17:00'}]}
        mock_mapear_horarios.return_value = {'EMP001': {'08:00': '17:00'}}
        
        # Mock API client methods
        self.manager.api_client.fetch_checkins = Mock(return_value=[
            {'employee': 'EMP001', 'employee_name': 'Test Employee', 'time': '2025-01-01T08:00:00'}
        ])
        self.manager.api_client.fetch_leave_applications = Mock(return_value=[])
        
        # Mock processor methods
        mock_df = pd.DataFrame({
            'employee': ['EMP001'],
            'dia': [datetime(2025, 1, 1).date()],
            'Nombre': ['Test Employee']
        })
        
        self.manager.processor.process_checkins_to_dataframe = Mock(return_value=mock_df)
        self.manager.processor.procesar_horarios_con_medianoche = Mock(return_value=mock_df)
        self.manager.processor.analizar_asistencia_con_horarios_cache = Mock(return_value=mock_df)
        self.manager.processor.aplicar_calculo_horas_descanso = Mock(return_value=mock_df)
        self.manager.processor.ajustar_horas_esperadas_con_permisos = Mock(return_value=mock_df)
        self.manager.processor.aplicar_regla_perdon_retardos = Mock(return_value=mock_df)
        self.manager.processor.clasificar_faltas_con_permisos = Mock(return_value=mock_df)
        
        # Mock report generator methods
        mock_resumen = pd.DataFrame({
            'employee': ['EMP001'],
            'Nombre': ['Test Employee'],
            'total_horas_trabajadas': ['08:00:00']
        })
        
        self.manager.report_generator.save_detailed_report = Mock(return_value='detailed_report.csv')
        self.manager.report_generator.generar_resumen_periodo = Mock(return_value=mock_resumen)
        self.manager.report_generator.generar_reporte_html = Mock(return_value='dashboard.html')
        self.manager.report_generator.generar_reporte_excel = Mock(return_value='report.xlsx')
        
        # Execute
        result = self.manager.generate_attendance_report(
            start_date='2025-01-01',
            end_date='2025-01-15',
            sucursal='Test Branch',
            device_filter='%test%'
        )
        
        # Verify
        assert result['success'] is True
        assert 'detailed_report' in result
        assert 'html_dashboard' in result
        assert 'excel_report' in result
        assert result['employees_processed'] == 2
        
        # Verify method calls
        self.manager.api_client.fetch_checkins.assert_called_once()
        self.manager.api_client.fetch_leave_applications.assert_called_once()
        self.manager.processor.process_checkins_to_dataframe.assert_called_once()
        self.manager.report_generator.save_detailed_report.assert_called_once()
    
    def test_generate_attendance_report_no_checkins(self):
        """Test handling when no check-ins are found."""
        
        # Mock API client to return no checkins
        self.manager.api_client.fetch_checkins = Mock(return_value=[])
        
        result = self.manager.generate_attendance_report(
            start_date='2025-01-01',
            end_date='2025-01-15',
            sucursal='Test Branch',
            device_filter='%test%'
        )
        
        assert result['success'] is False
        assert 'No se encontraron registros' in result['error']
    
    @patch('main.connect_db')
    def test_generate_attendance_report_db_connection_failure(self, mock_connect_db):
        """Test handling of database connection failure."""
        
        # Mock DB connection failure
        mock_connect_db.return_value = None
        
        # Mock API client to return checkins
        self.manager.api_client.fetch_checkins = Mock(return_value=[
            {'employee': 'EMP001', 'employee_name': 'Test Employee', 'time': '2025-01-01T08:00:00'}
        ])
        self.manager.api_client.fetch_leave_applications = Mock(return_value=[])
        
        result = self.manager.generate_attendance_report(
            start_date='2025-01-01',
            end_date='2025-01-15',
            sucursal='Test Branch',
            device_filter='%test%'
        )
        
        assert result['success'] is False
        assert 'conexión a la base de datos' in result['error']
    
    @patch('main.validate_api_credentials')
    def test_generate_attendance_report_api_validation_failure(self, mock_validate_api):
        """Test handling of API credential validation failure."""
        
        # Mock API validation to raise exception
        mock_validate_api.side_effect = Exception("Invalid API credentials")
        
        result = self.manager.generate_attendance_report(
            start_date='2025-01-01',
            end_date='2025-01-15',
            sucursal='Test Branch',
            device_filter='%test%'
        )
        
        assert result['success'] is False
        assert 'Invalid API credentials' in result['error']
    
    @patch('main.obtener_horarios_multi_quincena')
    def test_generate_attendance_report_no_schedules(self, mock_obtener_horarios):
        """Test handling when no schedules are found."""
        
        # Setup basic mocks
        with patch('main.validate_api_credentials'), \
             patch('main.connect_db', return_value=MagicMock()), \
             patch('main.obtener_codigos_empleados_api', return_value=['EMP001']), \
             patch('main.determine_period_type', return_value=(True, False)), \
             patch('main.mapear_horarios_por_empleado_multi', return_value={}):
            
            # Mock no schedules found
            mock_obtener_horarios.return_value = {'primera': [], 'segunda': []}
            
            self.manager.api_client.fetch_checkins = Mock(return_value=[
                {'employee': 'EMP001', 'employee_name': 'Test Employee', 'time': '2025-01-01T08:00:00'}
            ])
            self.manager.api_client.fetch_leave_applications = Mock(return_value=[])
            
            result = self.manager.generate_attendance_report(
                start_date='2025-01-01',
                end_date='2025-01-15',
                sucursal='Test Branch',
                device_filter='%test%'
            )
            
            assert result['success'] is False
            assert 'No hay horarios' in result['error']


class TestMainFunction:
    """Tests for the main() function."""
    
    @patch('main.AttendanceReportManager')
    def test_main_success(self, mock_manager_class):
        """Test successful execution of main function."""
        
        # Mock the manager instance and its method
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.generate_attendance_report.return_value = {
            'success': True,
            'detailed_report': 'test_detailed.csv',
            'summary_report': 'test_summary.csv',
            'html_dashboard': 'test_dashboard.html',
            'excel_report': 'test_report.xlsx',
            'employees_processed': 5,
            'days_processed': 15
        }
        
        # Execute main (should not raise exception)
        try:
            main()
            success = True
        except SystemExit:
            success = False
        
        assert success
        mock_manager.generate_attendance_report.assert_called_once()
    
    @patch('main.AttendanceReportManager')
    @patch('main.sys.exit')
    def test_main_failure(self, mock_exit, mock_manager_class):
        """Test main function with report generation failure."""
        
        # Mock the manager instance to return failure
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.generate_attendance_report.return_value = {
            'success': False,
            'error': 'Test error message'
        }
        
        # Execute main
        main()
        
        # Verify sys.exit was called
        mock_exit.assert_called_once_with(1)


class TestConfigurationValidation:
    """Tests for configuration and parameter validation."""
    
    def test_validate_api_credentials_success(self):
        """Test successful API credential validation."""
        
        with patch.dict('os.environ', {
            'ASIATECH_API_KEY': 'test_key',
            'ASIATECH_API_SECRET': 'test_secret'
        }):
            # Should not raise exception
            try:
                validate_api_credentials()
                success = True
            except Exception:
                success = False
            
            assert success
    
    def test_validate_api_credentials_missing(self):
        """Test API credential validation with missing credentials."""
        
        with patch('config.API_KEY', None), \
             patch('config.API_SECRET', None):
            with pytest.raises(ValueError):
                validate_api_credentials()


class TestEndToEndIntegration:
    """Integration tests for the full modular pipeline."""
    
    @pytest.mark.integration
    @patch('main.validate_api_credentials')
    @patch('main.connect_db')
    def test_full_pipeline_integration(self, mock_connect_db, mock_validate_api):
        """Test the complete pipeline with mocked external dependencies."""
        
        # This would be a more comprehensive integration test
        # that tests the full flow with realistic data
        
        # Setup realistic mock data
        mock_validate_api.return_value = None
        mock_db = MagicMock()
        mock_connect_db.return_value = mock_db
        
        manager = AttendanceReportManager()
        
        # Mock realistic checkin data
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
        
        with patch.object(manager.api_client, 'fetch_checkins', return_value=checkin_data), \
             patch.object(manager.api_client, 'fetch_leave_applications', return_value=[]), \
             patch('main.obtener_codigos_empleados_api', return_value=['EMP001']), \
             patch('main.procesar_permisos_empleados', return_value={}), \
             patch('main.determine_period_type', return_value=(True, False)), \
             patch('main.obtener_horarios_multi_quincena', return_value={'primera': [{'employee': 'EMP001'}]}), \
             patch('main.mapear_horarios_por_empleado_multi', return_value={'EMP001': {True: {1: {'hora_entrada': '08:00', 'hora_salida': '17:00', 'horas_totales': 8.0}}}}):
            
            result = manager.generate_attendance_report(
                start_date='2025-01-01',
                end_date='2025-01-01',
                sucursal='Test Branch',
                device_filter='%test%'
            )
            
            # Verify the result structure (basic integration test)
            assert isinstance(result, dict)
            assert 'success' in result