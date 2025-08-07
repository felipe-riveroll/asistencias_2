"""
Tests for api_client.py - APIClient class and related functions
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
import json
from datetime import datetime, date, timedelta

from api_client import APIClient, procesar_permisos_empleados


class TestAPIClient:
    """Tests for the APIClient class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = APIClient()
    
    def test_init(self):
        """Test APIClient initialization."""
        assert hasattr(self.client, 'checkin_url')
        assert hasattr(self.client, 'leave_url')
        assert hasattr(self.client, 'page_length')
        assert hasattr(self.client, 'timeout')
        assert self.client.page_length == 100
        assert self.client.timeout == 30
    
    @patch('api_client.requests.get')
    @patch.dict('os.environ', {
        'ASIATECH_API_KEY': 'test_key',
        'ASIATECH_API_SECRET': 'test_secret'
    })
    def test_fetch_checkins_success(self, mock_get):
        """Test successful checkin fetching."""
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'data': [
                {
                    'employee': 'EMP001',
                    'employee_name': 'John Doe',
                    'time': '2025-01-01T08:30:00Z'
                },
                {
                    'employee': 'EMP001',
                    'employee_name': 'John Doe',
                    'time': '2025-01-01T17:00:00Z'
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Execute
        result = self.client.fetch_checkins('2025-01-01', '2025-01-01', '%test%')
        
        # Verify
        assert len(result) == 2
        assert result[0]['employee'] == 'EMP001'
        assert result[0]['employee_name'] == 'John Doe'
        
        # Verify API call was made correctly
        mock_get.assert_called()
        call_args = mock_get.call_args
        assert 'headers' in call_args[1]
        assert 'Authorization' in call_args[1]['headers']
        assert 'params' in call_args[1]
    
    @patch('api_client.requests.get')
    @patch.dict('os.environ', {
        'ASIATECH_API_KEY': 'test_key',
        'ASIATECH_API_SECRET': 'test_secret'
    })
    def test_fetch_checkins_pagination(self, mock_get):
        """Test checkin fetching with pagination."""
        
        # Mock first page response
        first_response = Mock()
        first_response.raise_for_status.return_value = None
        first_response.json.return_value = {
            'data': [{'employee': f'EMP{i:03d}', 'employee_name': f'Employee {i}', 'time': '2025-01-01T08:30:00Z'} for i in range(100)]
        }
        
        # Mock second page response (empty)
        second_response = Mock()
        second_response.raise_for_status.return_value = None
        second_response.json.return_value = {'data': []}
        
        # Configure mock to return different responses for different calls
        mock_get.side_effect = [first_response, second_response]
        
        # Execute
        result = self.client.fetch_checkins('2025-01-01', '2025-01-01', '%test%')
        
        # Verify
        assert len(result) == 100
        assert mock_get.call_count == 2
    
    @patch('api_client.get_api_headers')
    @patch('api_client.requests.get')
    def test_fetch_checkins_missing_credentials(self, mock_get, mock_get_headers):
        """Test checkin fetching with missing API credentials."""
        
        # Mock missing credentials by making get_api_headers raise an exception
        mock_get_headers.side_effect = ValueError("Missing API credentials")
        
        result = self.client.fetch_checkins('2025-01-01', '2025-01-01', '%test%')
        
        # Should return empty list when credentials are missing
        assert result == []
        mock_get.assert_not_called()
    
    @patch('api_client.requests.get')
    @patch.dict('os.environ', {
        'ASIATECH_API_KEY': 'test_key',
        'ASIATECH_API_SECRET': 'test_secret'
    })
    def test_fetch_checkins_api_error(self, mock_get):
        """Test checkin fetching with API error."""
        
        # Mock API error
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        # Execute
        result = self.client.fetch_checkins('2025-01-01', '2025-01-01', '%test%')
        
        # Should return empty list on API error
        assert result == []
    
    @patch('api_client.requests.get')
    @patch.dict('os.environ', {
        'ASIATECH_API_KEY': 'test_key',
        'ASIATECH_API_SECRET': 'test_secret'
    })
    def test_fetch_leave_applications_success(self, mock_get):
        """Test successful leave application fetching."""
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'data': [
                {
                    'employee': 'EMP001',
                    'employee_name': 'John Doe',
                    'leave_type': 'Vacations',
                    'from_date': '2025-01-01',
                    'to_date': '2025-01-01',
                    'status': 'Approved',
                    'half_day': 0
                },
                {
                    'employee': 'EMP002',
                    'employee_name': 'Jane Smith',
                    'leave_type': 'Sick Leave',
                    'from_date': '2025-01-02',
                    'to_date': '2025-01-03',
                    'status': 'Approved',
                    'half_day': 1
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Execute
        result = self.client.fetch_leave_applications('2025-01-01', '2025-01-03')
        
        # Verify
        assert len(result) == 2
        assert result[0]['employee'] == 'EMP001'
        assert result[0]['leave_type'] == 'Vacations'
        assert result[1]['half_day'] == 1
        
        # Verify API call was made correctly
        mock_get.assert_called()
    
    @patch('api_client.requests.get')
    @patch.dict('os.environ', {
        'ASIATECH_API_KEY': 'test_key',
        'ASIATECH_API_SECRET': 'test_secret'
    })
    def test_fetch_leave_applications_timeout(self, mock_get):
        """Test leave application fetching with timeout."""
        
        # Mock timeout on first call, success on second
        timeout_response = requests.exceptions.Timeout("Timeout")
        success_response = Mock()
        success_response.raise_for_status.return_value = None
        success_response.json.return_value = {'data': []}
        
        mock_get.side_effect = [timeout_response, success_response]
        
        # Execute
        result = self.client.fetch_leave_applications('2025-01-01', '2025-01-03')
        
        # Should retry after timeout
        assert result == []
        assert mock_get.call_count == 2
    
    @patch('api_client.get_api_headers')
    @patch('api_client.requests.get')
    def test_fetch_leave_applications_missing_credentials(self, mock_get, mock_get_headers):
        """Test leave application fetching with missing credentials."""
        
        # Mock missing credentials by making get_api_headers raise an exception
        mock_get_headers.side_effect = ValueError("Missing API credentials")
        
        result = self.client.fetch_leave_applications('2025-01-01', '2025-01-03')
        
        # Should return empty list when credentials are missing
        assert result == []
        mock_get.assert_not_called()
    
    @patch('api_client.requests.get')
    @patch.dict('os.environ', {
        'ASIATECH_API_KEY': 'test_key',
        'ASIATECH_API_SECRET': 'test_secret'
    })
    def test_fetch_leave_applications_api_error(self, mock_get):
        """Test leave application fetching with API error."""
        
        # Mock API error
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        # Execute
        result = self.client.fetch_leave_applications('2025-01-01', '2025-01-03')
        
        # Should return empty list on API error
        assert result == []


class TestProcesarPermisosEmpleados:
    """Tests for the procesar_permisos_empleados function."""
    
    def test_procesar_permisos_empleados_empty(self):
        """Test processing empty leave data."""
        result = procesar_permisos_empleados([])
        assert result == {}
    
    def test_procesar_permisos_empleados_full_day_leave(self):
        """Test processing full day leave."""
        leave_data = [
            {
                'employee': 'EMP001',
                'employee_name': 'John Doe',
                'leave_type': 'Vacations',
                'from_date': '2025-01-01',
                'to_date': '2025-01-02',
                'status': 'Approved',
                'half_day': 0
            }
        ]
        
        result = procesar_permisos_empleados(leave_data)
        
        # Verify structure
        assert 'EMP001' in result
        assert date(2025, 1, 1) in result['EMP001']
        assert date(2025, 1, 2) in result['EMP001']
        
        # Verify full day leave details
        leave_info = result['EMP001'][date(2025, 1, 1)]
        assert leave_info['leave_type'] == 'Vacations'
        assert leave_info['is_half_day'] is False
        assert leave_info['dias_permiso'] == 1.0
        assert leave_info['employee_name'] == 'John Doe'
    
    def test_procesar_permisos_empleados_half_day_leave(self):
        """Test processing half day leave."""
        leave_data = [
            {
                'employee': 'EMP001',
                'employee_name': 'John Doe',
                'leave_type': 'Personal Leave',
                'from_date': '2025-01-01',
                'to_date': '2025-01-01',
                'status': 'Approved',
                'half_day': 1
            }
        ]
        
        result = procesar_permisos_empleados(leave_data)
        
        # Verify structure
        assert 'EMP001' in result
        assert date(2025, 1, 1) in result['EMP001']
        
        # Verify half day leave details
        leave_info = result['EMP001'][date(2025, 1, 1)]
        assert leave_info['leave_type'] == 'Personal Leave'
        assert leave_info['is_half_day'] is True
        assert leave_info['dias_permiso'] == 0.5
    
    def test_procesar_permisos_empleados_multiple_employees(self):
        """Test processing leaves for multiple employees."""
        leave_data = [
            {
                'employee': 'EMP001',
                'employee_name': 'John Doe',
                'leave_type': 'Vacations',
                'from_date': '2025-01-01',
                'to_date': '2025-01-01',
                'status': 'Approved',
                'half_day': 0
            },
            {
                'employee': 'EMP002',
                'employee_name': 'Jane Smith',
                'leave_type': 'Sick Leave',
                'from_date': '2025-01-01',
                'to_date': '2025-01-01',
                'status': 'Approved',
                'half_day': 1
            }
        ]
        
        result = procesar_permisos_empleados(leave_data)
        
        # Verify both employees are processed
        assert 'EMP001' in result
        assert 'EMP002' in result
        assert date(2025, 1, 1) in result['EMP001']
        assert date(2025, 1, 1) in result['EMP002']
        
        # Verify different leave types
        assert result['EMP001'][date(2025, 1, 1)]['leave_type'] == 'Vacations'
        assert result['EMP002'][date(2025, 1, 1)]['leave_type'] == 'Sick Leave'
        
        # Verify different half_day settings
        assert result['EMP001'][date(2025, 1, 1)]['is_half_day'] is False
        assert result['EMP002'][date(2025, 1, 1)]['is_half_day'] is True
    
    def test_procesar_permisos_empleados_date_range_leave(self):
        """Test processing leave that spans multiple days."""
        leave_data = [
            {
                'employee': 'EMP001',
                'employee_name': 'John Doe',
                'leave_type': 'Vacations',
                'from_date': '2025-01-01',
                'to_date': '2025-01-03',
                'status': 'Approved',
                'half_day': 0
            }
        ]
        
        result = procesar_permisos_empleados(leave_data)
        
        # Verify all dates in range are included
        assert 'EMP001' in result
        assert date(2025, 1, 1) in result['EMP001']
        assert date(2025, 1, 2) in result['EMP001']
        assert date(2025, 1, 3) in result['EMP001']
        
        # Verify all dates have same leave info
        for test_date in [date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3)]:
            leave_info = result['EMP001'][test_date]
            assert leave_info['leave_type'] == 'Vacations'
            assert leave_info['from_date'] == date(2025, 1, 1)
            assert leave_info['to_date'] == date(2025, 1, 3)
            assert leave_info['is_half_day'] is False
            assert leave_info['dias_permiso'] == 1.0
    
    def test_procesar_permisos_empleados_mixed_leave_types(self):
        """Test processing mixed full day and half day leaves."""
        leave_data = [
            {
                'employee': 'EMP001',
                'employee_name': 'John Doe',
                'leave_type': 'Vacations',
                'from_date': '2025-01-01',
                'to_date': '2025-01-02',
                'status': 'Approved',
                'half_day': 0  # Full day
            },
            {
                'employee': 'EMP001',
                'employee_name': 'John Doe',
                'leave_type': 'Personal Leave',
                'from_date': '2025-01-03',
                'to_date': '2025-01-03',
                'status': 'Approved',
                'half_day': 1  # Half day
            }
        ]
        
        result = procesar_permisos_empleados(leave_data)
        
        # Verify all dates are processed
        assert 'EMP001' in result
        assert len(result['EMP001']) == 3  # Jan 1, 2, 3
        
        # Verify full day leaves
        assert result['EMP001'][date(2025, 1, 1)]['is_half_day'] is False
        assert result['EMP001'][date(2025, 1, 2)]['is_half_day'] is False
        assert result['EMP001'][date(2025, 1, 1)]['dias_permiso'] == 1.0
        assert result['EMP001'][date(2025, 1, 2)]['dias_permiso'] == 1.0
        
        # Verify half day leave
        assert result['EMP001'][date(2025, 1, 3)]['is_half_day'] is True
        assert result['EMP001'][date(2025, 1, 3)]['dias_permiso'] == 0.5
    
    def test_procesar_permisos_empleados_normalization(self):
        """Test leave type normalization."""
        leave_data = [
            {
                'employee': 'EMP001',
                'employee_name': 'John Doe',
                'leave_type': 'Permiso sin goce de sueldo',
                'from_date': '2025-01-01',
                'to_date': '2025-01-01',
                'status': 'Approved',
                'half_day': 0
            }
        ]
        
        result = procesar_permisos_empleados(leave_data)
        
        # Verify leave type normalization
        leave_info = result['EMP001'][date(2025, 1, 1)]
        assert leave_info['leave_type'] == 'Permiso sin goce de sueldo'
        assert 'leave_type_normalized' in leave_info
        # The normalization should be handled by the normalize_leave_type function


class TestAPIClientIntegration:
    """Integration tests for APIClient with realistic scenarios."""
    
    @pytest.mark.integration
    def test_full_api_workflow(self):
        """Test complete API workflow with both checkins and leaves."""
        
        client = APIClient()
        
        # This would typically use real API calls in a proper integration test
        # For now, we'll mock to test the workflow
        
        with patch.object(client, 'fetch_checkins') as mock_checkins, \
             patch.object(client, 'fetch_leave_applications') as mock_leaves:
            
            # Mock realistic data
            mock_checkins.return_value = [
                {'employee': 'EMP001', 'employee_name': 'John Doe', 'time': '2025-01-01T08:30:00Z'},
                {'employee': 'EMP001', 'employee_name': 'John Doe', 'time': '2025-01-01T17:00:00Z'}
            ]
            
            mock_leaves.return_value = [
                {
                    'employee': 'EMP001',
                    'employee_name': 'John Doe',
                    'leave_type': 'Vacations',
                    'from_date': '2025-01-02',
                    'to_date': '2025-01-02',
                    'status': 'Approved',
                    'half_day': 0
                }
            ]
            
            # Execute workflow
            checkins = client.fetch_checkins('2025-01-01', '2025-01-02', '%test%')
            leaves = client.fetch_leave_applications('2025-01-01', '2025-01-02')
            processed_leaves = procesar_permisos_empleados(leaves)
            
            # Verify workflow results
            assert len(checkins) == 2
            assert len(leaves) == 1
            assert 'EMP001' in processed_leaves
            assert date(2025, 1, 2) in processed_leaves['EMP001']